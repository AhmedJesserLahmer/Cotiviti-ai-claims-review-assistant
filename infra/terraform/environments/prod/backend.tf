# Remote state with locking. Create the bucket and table once, out of band.
terraform {
  backend "s3" {
    bucket         = "claims-review-terraform-state"
    key            = "prod/platform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "claims-review-terraform-locks"
    encrypt        = true
  }
}
