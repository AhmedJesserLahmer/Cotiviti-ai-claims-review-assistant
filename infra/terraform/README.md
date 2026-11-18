# Terraform: managed platform on AWS

`modules/claims-platform` provisions what the Helm chart expects in production:

| Resource | Used by |
|---|---|
| VPC (3 AZs, private/public subnets, NAT) | everything |
| EKS + managed node group (IMDSv2 only), VPC CNI with NetworkPolicy enforcement | the chart |
| EBS and EFS CSI drivers (IRSA) | MongoDB/Redis PVCs (dev), model registry RWX volume |
| EFS file system (encrypted) | `mlService.models.persistence` |
| ElastiCache Redis 7 (Multi-AZ, TLS, at-rest encryption, `noeviction`) | `redis.externalUrl` |
| Secrets Manager entry + IRSA role | External Secrets → release Secret |

MongoDB is expected to be a managed replica set (MongoDB Atlas or Amazon DocumentDB)
provisioned separately; set `mongodb.externalUri`.

```bash
cd infra/terraform/environments/prod
cp terraform.tfvars.example terraform.tfvars   # edit
terraform init && terraform plan -out plan.tfplan
terraform apply plan.tfplan
```

Secret values are never in Terraform: after apply, set them with
`aws secretsmanager put-secret-value --secret-id claims-review/claims-review-prod --secret-string file://secrets.json`.
