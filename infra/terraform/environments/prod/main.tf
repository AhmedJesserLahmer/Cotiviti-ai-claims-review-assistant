provider "aws" {
  region = var.region
  default_tags {
    tags = { environment = "prod", project = "claims-review" }
  }
}

variable "region" {
  type    = string
  default = "us-east-1"
}

variable "api_allowed_cidrs" {
  description = "Office/VPN CIDRs allowed to reach the Kubernetes API."
  type        = list(string)
}

module "platform" {
  source = "../../modules/claims-platform"

  name              = "claims-review-prod"
  region            = var.region
  azs               = ["${var.region}a", "${var.region}b", "${var.region}c"]
  api_allowed_cidrs = var.api_allowed_cidrs
  app_namespace     = "claims-review-prod"
}

output "platform" {
  value = module.platform
}
