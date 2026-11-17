variable "name" {
  description = "Base name for every resource (e.g. claims-review-prod)."
  type        = string
}

variable "region" {
  description = "AWS region."
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR of the platform VPC."
  type        = string
  default     = "10.40.0.0/16"
}

variable "azs" {
  description = "Availability zones (three for production)."
  type        = list(string)
}

variable "single_nat_gateway" {
  description = "One NAT gateway instead of one per AZ (cheaper, less resilient)."
  type        = bool
  default     = false
}

variable "kubernetes_version" {
  description = "EKS control-plane version."
  type        = string
  default     = "1.31"
}

variable "api_allowed_cidrs" {
  description = "CIDRs allowed to reach the public Kubernetes API endpoint."
  type        = list(string)
}

variable "node_instance_types" {
  description = "Instance types of the managed node group."
  type        = list(string)
  default     = ["m6i.large"]
}

variable "node_min_size" {
  type    = number
  default = 3
}

variable "node_max_size" {
  type    = number
  default = 8
}

variable "node_desired_size" {
  type    = number
  default = 3
}

variable "redis_node_type" {
  description = "ElastiCache node type for the job queue / caches."
  type        = string
  default     = "cache.t4g.small"
}

variable "app_namespace" {
  description = "Kubernetes namespace of the Helm release."
  type        = string
  default     = "claims-review-prod"
}

variable "tags" {
  description = "Tags added to every resource."
  type        = map(string)
  default     = {}
}
