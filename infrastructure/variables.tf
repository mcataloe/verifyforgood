variable "aws_region" {
  description = "AWS region for provider operations."
  type        = string
  default     = null
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
  description = "S3 bucket that already contains IRS EO BMF source files."
  type        = string
}

variable "athena_results_bucket_name" {
  description = "Name for the S3 bucket that stores Athena query results."
  type        = string
}

variable "glue_database_name" {
  description = "Glue Data Catalog database name for IRS EO BMF metadata."
  type        = string
}

variable "eo1_prefix" {
  description = "S3 prefix for EO1 CSV files (without bucket name)."
  type        = string
  default     = "eo_bmf/eo1/"
}

variable "eo2_prefix" {
  description = "S3 prefix for EO2 CSV files (without bucket name)."
  type        = string
  default     = "eo_bmf/eo2/"
}

variable "eo3_prefix" {
  description = "S3 prefix for EO3 CSV files (without bucket name)."
  type        = string
  default     = "eo_bmf/eo3/"
}

variable "eo4_prefix" {
  description = "S3 prefix for EO4 CSV files (without bucket name)."
  type        = string
  default     = "eo_bmf/eo4/"
}

variable "eo_pr_prefix" {
  description = "S3 prefix for EO_PR CSV files (without bucket name)."
  type        = string
  default     = "eo_bmf/eo_pr/"
}

variable "eo_xx_prefix" {
  description = "S3 prefix for EO_XX CSV files (without bucket name)."
  type        = string
  default     = "eo_bmf/eo_xx/"
}

# Compatibility variables already referenced by existing files in this repository.
variable "region" {
  description = "Backward-compatible alias for aws_region."
  type        = string
  default     = "us-east-1"
}

variable "env" {
  description = "Backward-compatible alias used by existing non-Athena resources."
  type        = string
  default     = null
}

variable "domain_name" {
  description = "Existing Route53/API variable used by other resources in this repo."
  type        = string
  default     = ""
}