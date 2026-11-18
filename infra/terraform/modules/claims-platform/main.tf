locals {
  tags = merge(var.tags, { "app.kubernetes.io/part-of" = "claims-review", "managed-by" = "terraform" })

  # Secret consumed by External Secrets (keys: GROQ_API_KEY, INTERNAL_TOKEN, AUDIT_HMAC_KEY, JWT_SECRET).
  secret_name = "claims-review/${var.app_namespace}"
}

# ---------------------------------------------------------------------------------------
# Network: private subnets for nodes and data stores, public subnets for load balancers.
# ---------------------------------------------------------------------------------------
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.16"

  name = var.name
  cidr = var.vpc_cidr
  azs  = var.azs

  private_subnets = [for i, _ in var.azs : cidrsubnet(var.vpc_cidr, 4, i)]
  public_subnets  = [for i, _ in var.azs : cidrsubnet(var.vpc_cidr, 8, 200 + i)]

  enable_nat_gateway   = true
  single_nat_gateway   = var.single_nat_gateway
  enable_dns_hostnames = true

  public_subnet_tags  = { "kubernetes.io/role/elb" = 1 }
  private_subnet_tags = { "kubernetes.io/role/internal-elb" = 1 }

  tags = local.tags
}

# ---------------------------------------------------------------------------------------
# EKS cluster with managed nodes and the CSI drivers the chart needs.
# ---------------------------------------------------------------------------------------
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.31"

  cluster_name    = var.name
  cluster_version = var.kubernetes_version

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  cluster_endpoint_public_access           = true
  cluster_endpoint_public_access_cidrs     = var.api_allowed_cidrs
  enable_cluster_creator_admin_permissions = true
  enable_irsa                              = true

  cluster_addons = {
    coredns    = { most_recent = true }
    kube-proxy = { most_recent = true }

    vpc-cni = {
      most_recent = true

      # Enforce Kubernetes NetworkPolicies natively (the chart is default-deny).
      configuration_values = jsonencode({ enableNetworkPolicy = "true" })
    }

    aws-ebs-csi-driver = {
      most_recent              = true
      service_account_role_arn = module.ebs_csi_irsa.iam_role_arn
    }

    aws-efs-csi-driver = {
      most_recent              = true
      service_account_role_arn = module.efs_csi_irsa.iam_role_arn
    }
  }

  eks_managed_node_groups = {
    default = {
      instance_types = var.node_instance_types
      capacity_type  = "ON_DEMAND"
      min_size       = var.node_min_size
      max_size       = var.node_max_size
      desired_size   = var.node_desired_size

      # IMDSv2 only, so pods cannot borrow the node's IAM role.
      metadata_options = {
        http_tokens                 = "required"
        http_put_response_hop_limit = 1
      }
    }
  }

  tags = local.tags
}

module "ebs_csi_irsa" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.48"

  role_name             = "${var.name}-ebs-csi"
  attach_ebs_csi_policy = true

  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["kube-system:ebs-csi-controller-sa"]
    }
  }

  tags = local.tags
}

module "efs_csi_irsa" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.48"

  role_name             = "${var.name}-efs-csi"
  attach_efs_csi_policy = true

  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["kube-system:efs-csi-controller-sa"]
    }
  }

  tags = local.tags
}

# ---------------------------------------------------------------------------------------
# EFS: ReadWriteMany volume for the ML model registry (training CronJob + ml-service).
# ---------------------------------------------------------------------------------------
resource "aws_security_group" "efs" {
  name_prefix = "${var.name}-efs-"
  description = "NFS from EKS nodes to the model registry"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description     = "NFS from nodes"
    from_port       = 2049
    to_port         = 2049
    protocol        = "tcp"
    security_groups = [module.eks.node_security_group_id]
  }

  tags = local.tags
}

resource "aws_efs_file_system" "models" {
  creation_token   = "${var.name}-models"
  encrypted        = true
  performance_mode = "generalPurpose"
  throughput_mode  = "elastic"

  lifecycle_policy {
    transition_to_ia = "AFTER_30_DAYS"
  }

  tags = merge(local.tags, { Name = "${var.name}-models" })
}

resource "aws_efs_mount_target" "models" {
  for_each        = toset(module.vpc.private_subnets)
  file_system_id  = aws_efs_file_system.models.id
  subnet_id       = each.value
  security_groups = [aws_security_group.efs.id]
}

# ---------------------------------------------------------------------------------------
# Redis (job queue, LLM cache, rate limits): encrypted in transit and at rest, Multi-AZ.
# ---------------------------------------------------------------------------------------
resource "aws_elasticache_subnet_group" "redis" {
  name       = "${var.name}-redis"
  subnet_ids = module.vpc.private_subnets
}

resource "aws_security_group" "redis" {
  name_prefix = "${var.name}-redis-"
  description = "Redis from EKS nodes only"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description     = "Redis TLS from nodes"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [module.eks.node_security_group_id]
  }

  tags = local.tags
}

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id       = "${var.name}-redis"
  description                = "claims-review job queue, LLM cache and rate limits"
  engine                     = "redis"
  engine_version             = "7.1"
  node_type                  = var.redis_node_type
  num_cache_clusters         = 2
  automatic_failover_enabled = true
  multi_az_enabled           = true
  transit_encryption_enabled = true
  at_rest_encryption_enabled = true
  subnet_group_name          = aws_elasticache_subnet_group.redis.name
  security_group_ids         = [aws_security_group.redis.id]
  snapshot_retention_limit   = 3

  # The job queue must not lose entries under memory pressure.
  parameter_group_name = aws_elasticache_parameter_group.redis.name
  tags                 = local.tags
}

resource "aws_elasticache_parameter_group" "redis" {
  name   = "${var.name}-redis7"
  family = "redis7"

  parameter {
    name  = "maxmemory-policy"
    value = "noeviction"
  }
}

# ---------------------------------------------------------------------------------------
# Secrets: one Secrets Manager entry read by External Secrets through IRSA.
# Values are set out of band (console/CLI), never in Terraform state.
# ---------------------------------------------------------------------------------------
resource "aws_secretsmanager_secret" "app" {
  name                    = local.secret_name
  description             = "claims-review application secrets (GROQ_API_KEY, INTERNAL_TOKEN, AUDIT_HMAC_KEY, JWT_SECRET)"
  recovery_window_in_days = 7
  tags                    = local.tags
}

data "aws_iam_policy_document" "external_secrets" {
  statement {
    sid       = "ReadClaimsReviewSecret"
    actions   = ["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"]
    resources = [aws_secretsmanager_secret.app.arn]
  }
}

resource "aws_iam_policy" "external_secrets" {
  name   = "${var.name}-external-secrets"
  policy = data.aws_iam_policy_document.external_secrets.json
  tags   = local.tags
}

module "external_secrets_irsa" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.48"

  role_name = "${var.name}-external-secrets"

  role_policy_arns = {
    read = aws_iam_policy.external_secrets.arn
  }

  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["external-secrets:external-secrets"]
    }
  }

  tags = local.tags
}
