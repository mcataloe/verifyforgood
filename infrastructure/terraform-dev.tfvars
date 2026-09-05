environment                     = "dev"
resource_name_strategy          = "standardized"
form990_schedule_expression     = "cron(30 4 * * ? *)"
form990_execution_mode          = "orchestrated"
form990_incremental_year_window = 1
refresh_schedule_expression     = "cron(0 6 * * ? *)"

# Terraform-owned dev network. The legacy ECS/RDS id inputs remain populated
# only to satisfy compatibility validations; managed-network locals supersede
# them whenever environment_network_enabled=true.
environment_network_enabled              = true
environment_vpc_cidr                     = "10.10.0.0/16"
environment_public_subnet_cidrs          = ["10.10.0.0/24", "10.10.1.0/24"]
environment_private_subnet_cidrs         = ["10.10.10.0/24", "10.10.11.0/24"]
environment_single_nat_gateway_enabled   = true
environment_s3_gateway_endpoint_enabled  = true
api_ecs_vpc_id                           = "managed-by-environment-network"
api_ecs_public_subnet_ids                = ["managed-public-1", "managed-public-2"]
api_ecs_private_subnet_ids               = ["managed-private-1", "managed-private-2"]
platform_postgres_vpc_id                 = "managed-by-environment-network"
platform_postgres_private_subnet_ids     = ["managed-private-1", "managed-private-2"]

# Dev application runtime.
api_ecs_enabled         = true
api_ecs_image_uri       = ""
api_ecs_secret_arns     = {}
platform_postgres_enabled = true

# Per-environment DNS. The parent verifyforgood.com hosted zone is intentionally
# external to this stack. Create it first, then this stack delegates dev into
# the environment-specific hosted zone.
enable_custom_domain              = true
environment_route53_zone_enabled  = true
parent_route53_zone_name          = "verifyforgood.com."
parent_route53_delegation_enabled = true

# Customer upload/RAG foundation. Partitioning between tenant-wide and
# individual-user documents remains intentionally undefined until that product
# contract is designed.
customer_documents_bucket_enabled = true
customer_documents_force_destroy  = false
bedrock_runtime_access_enabled     = false
bedrock_allowed_model_arns         = []

# GitHub Actions OIDC bootstrap. If the account already has the GitHub OIDC
# provider, set github_oidc_manage_provider=false and provide its ARN instead.
github_oidc_deploy_role_enabled = true
github_oidc_manage_provider      = true
github_environment_name          = "dev"

cors_allowed_origins = [
  "http://localhost:5173",
  "http://127.0.0.1:5173",
  "http://localhost:5174",
  "http://127.0.0.1:5174",
  "https://dev.verifyforgood.com",
]
