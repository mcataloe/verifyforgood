variable "aws_region" {
  description = "AWS region for provider operations."
  type        = string
}

variable "project_name" {
  description = "Project identifier used for naming resources."
  type        = string
}

variable "environment" {
  description = "Deployment environment (for example: dev, staging, prod)."
  type        = string
}

variable "source_data_bucket_name" {
  description = "S3 bucket that stores the IRS EO BMF CSV source files."
  type        = string
}

variable "source_data_prefix" {
  description = "Shared S3 prefix under the source bucket where all EO BMF CSV files are stored."
  type        = string
  default     = "eo_bmf/"
}

variable "athena_results_bucket_name" {
  description = "Name for the S3 bucket that stores Athena query results."
  type        = string
}

variable "glue_database_name" {
  description = "Glue Data Catalog database name for IRS EO BMF metadata."
  type        = string
  default     = "irs_nonprofits"
}

variable "athena_workgroup_name" {
  description = "Athena workgroup name used for EO BMF queries."
  type        = string
  default     = "irs-eo-bmf"
}

# Existing variables still used by other resources in this repo.
variable "domain_name" {
  description = "Existing Route53/API variable used by other resources in this repo."
  type        = string
  default     = ""
}

variable "enable_custom_domain" {
  description = "Whether to manage ACM/API custom domain/Route53 resources."
  type        = bool
  default     = false
}

variable "base_name" {
  description = "Base name for resources."
  type        = string
}

variable "eo1_prefix" {
  description = "Base name for resources."
  type        = string
}

variable "eo2_prefix" {
  description = "Base name for resources."
  type        = string
}

variable "eo3_prefix" {
  description = "Base name for resources."
  type        = string
}

variable "eo4_prefix" {
  description = "Base name for resources."
  type        = string
}

variable "eo_pr_prefix" {
  description = "Base name for resources."
  type        = string
}

variable "eo_xx_prefix" {
  description = "Base name for resources."
  type        = string
}
