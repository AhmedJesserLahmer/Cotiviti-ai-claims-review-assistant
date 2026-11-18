output "cluster_name" {
  value = module.eks.cluster_name
}

output "cluster_endpoint" {
  value = module.eks.cluster_endpoint
}

output "oidc_provider_arn" {
  value = module.eks.oidc_provider_arn
}

output "redis_url" {
  description = "Value for redis.externalUrl in values-prod.yaml (TLS)."
  value       = "rediss://${aws_elasticache_replication_group.redis.primary_endpoint_address}:6379/0"
}

output "models_efs_id" {
  description = "EFS file system for the model-registry StorageClass."
  value       = aws_efs_file_system.models.id
}

output "app_secret_name" {
  description = "secrets.externalSecrets.remoteKey in values-prod.yaml."
  value       = aws_secretsmanager_secret.app.name
}

output "external_secrets_role_arn" {
  description = "Annotate the external-secrets service account with this role."
  value       = module.external_secrets_irsa.iam_role_arn
}
