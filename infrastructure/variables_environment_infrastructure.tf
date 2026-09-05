variable "environment_network_enabled" {
  description = "Whether Terraform manages the environment VPC, subnets, routing, NAT gateway, and cost-conscious VPC endpoints."
  type        = bool
  default     = false
}

variable "environment_vpc_cidr" {
  description = "CIDR block for the environment VPC. Keep environment CIDRs non-overlapping to preserve future peering/transit options."
  type        = string
  default     = "10.10.0.0/16"
}

variable "environment_public_subnet_cidrs" {
  description = "Public subnet CIDRs used by the ALB and the single development NAT gateway."
  type        = list(string)
  default     = ["10.10.0.0/24", "10.10.1.0/24"]

  validation {
    condition     = !var.environment_network_enabled || length(var.environment_public_subnet_cidrs) >= 2
    error_message = "environment_public_subnet_cidrs must contain at least two subnets when environment_network_enabled=true."
  }
}

variable "environment_private_subnet_cidrs" {
  description = "Private subnet CIDRs used by ECS and RDS."
  type        = list(string)
  default     = ["10.10.10.0/24", "10.10.11.0/24"]

  validation {
    condition     = !var.environment_network_enabled || length(var.environment_private_subnet_cidrs) >= 2
    error_message = "environment_private_subnet_cidrs must contain at least two subnets when environment_network_enabled=true."
  }
}

variable "environment_single_nat_gateway_enabled" {
  description = "Whether to provision one NAT gateway for private-subnet internet egress. Dev intentionally uses one NAT gateway to reduce fixed cost; production should revisit HA."
  type        = bool
  default     = true
}

variable "environment_s3_gateway_endpoint_enabled" {
  description = "Whether to provision the no-hourly-charge S3 Gateway VPC endpoint and associate it with the private route table."
  type        = bool
  default     = true
}

variable "environment_route53_zone_enabled" {
  description = "Whether Terraform manages a public Route53 hosted zone for this environment, such as dev.verifyforgood.com."
  type        = bool
  default     = false
}

variable "parent_route53_zone_name" {
  description = "Optional existing parent public Route53 hosted-zone name used only for subdomain delegation, such as verifyforgood.com. Leave empty until the parent hosted zone exists."
  type        = string
  default     = ""
}

variable "parent_route53_delegation_enabled" {
  description = "Whether Terraform should create the environment-zone NS delegation record in the existing parent hosted zone. Requires parent_route53_zone_name."
  type        = bool
  default     = false

  validation {
    condition     = !var.parent_route53_delegation_enabled || trim(var.parent_route53_zone_name, " ") != ""
    error_message = "parent_route53_zone_name must be set when parent_route53_delegation_enabled=true."
  }
}

variable "customer_documents_bucket_enabled" {
  description = "Whether to provision the private customer-document S3 bucket used by future upload/RAG flows. Tenant and user partitioning is intentionally not defined here."
  type        = bool
  default     = false
}

variable "customer_documents_force_destroy" {
  description = "Whether Terraform may delete the customer-document bucket when objects remain. Keep false outside intentionally disposable environments."
  type        = bool
  default     = false
}

variable "bedrock_runtime_access_enabled" {
  description = "Whether the ECS API task role may invoke explicitly listed Amazon Bedrock foundation models. No Bedrock interface endpoint, Knowledge Base, vector store, ingestion flow, or tenancy model is created by this flag."
  type        = bool
  default     = false
}

variable "bedrock_allowed_model_arns" {
  description = "Explicit Bedrock model ARNs the API task may invoke. Keep empty until a model is selected."
  type        = list(string)
  default     = []

  validation {
    condition     = !var.bedrock_runtime_access_enabled || length(var.bedrock_allowed_model_arns) > 0
    error_message = "bedrock_allowed_model_arns must contain at least one explicit model ARN when bedrock_runtime_access_enabled=true."
  }
}

variable "github_oidc_deploy_role_enabled" {
  description = "Whether Terraform manages the GitHub Actions dev deployment IAM role. A one-time authenticated bootstrap apply is required before GitHub can assume this role."
  type        = bool
  default     = false
}

variable "github_oidc_manage_provider" {
  description = "Whether Terraform creates the account-level GitHub Actions OIDC provider. Leave false when the AWS account already has token.actions.githubusercontent.com configured."
  type        = bool
  default     = false
}

variable "github_oidc_provider_arn" {
  description = "Existing GitHub Actions OIDC provider ARN. Required when github_oidc_deploy_role_enabled=true and github_oidc_manage_provider=false."
  type        = string
  default     = ""

  validation {
    condition     = !var.github_oidc_deploy_role_enabled || var.github_oidc_manage_provider || trim(var.github_oidc_provider_arn, " ") != ""
    error_message = "github_oidc_provider_arn must be set when github_oidc_deploy_role_enabled=true and github_oidc_manage_provider=false."
  }
}

variable "github_repository" {
  description = "GitHub repository allowed to assume the environment deploy role, in owner/repository form."
  type        = string
  default     = "mcataloe/verifyforgood"
}

variable "github_environment_name" {
  description = "GitHub Environment name allowed to assume the deploy role."
  type        = string
  default     = "dev"
}

variable "github_dev_deploy_role_name" {
  description = "IAM role name assumed by the GitHub dev deployment workflow."
  type        = string
  default     = "verifyforgood-github-dev-deploy"
}

variable "terraform_state_bucket_name" {
  description = "Existing Terraform remote-state S3 bucket used by the GitHub deploy role. This stack does not bootstrap its own backend bucket."
  type        = string
  default     = "charitystatusapi-dev"
}

variable "terraform_state_lock_table_name" {
  description = "Existing Terraform state-lock DynamoDB table used by the current backend configuration."
  type        = string
  default     = "charitystatusapi-dev"
}
