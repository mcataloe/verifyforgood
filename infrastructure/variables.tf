variable "aws_region" {
  description = "AWS region for provider operations."
  type        = string
}

variable "environment" {
  description = "Deployment environment (for example: dev, staging, prod)."
  type        = string
}

variable "source_data_prefix" {
  description = "Shared S3 prefix under the source bucket where all EO BMF CSV files are stored."
  type        = string
  default     = "eo_bmf/"
}

variable "form990_raw_prefix" {
  description = "S3 prefix for raw Form 990 XML payloads."
  type        = string
  default     = "form990/raw/"
}

variable "form990_metadata_prefix" {
  description = "S3 prefix for normalized Form 990 metadata records."
  type        = string
  default     = "form990/normalized/metadata/"
}

variable "form990_manifest_prefix" {
  description = "S3 prefix for Form 990 parse manifests/status outputs."
  type        = string
  default     = "form990/normalized/manifests/"
}

variable "form990_metrics_prefix" {
  description = "S3 prefix for derived Form 990 financial metrics dataset."
  type        = string
  default     = "form990/normalized/metrics/"
}

variable "form990_governance_prefix" {
  description = "S3 prefix for normalized Form 990 governance flags dataset."
  type        = string
  default     = "form990/normalized/governance/"
}

variable "form990_quality_prefix" {
  description = "S3 prefix for normalized Form 990 filing quality indicators dataset."
  type        = string
  default     = "form990/normalized/quality/"
}

variable "athena_workgroup_name" {
  description = "Athena workgroup name used for EO BMF queries."
  type        = string
  default     = "irs-eo-bmf"
}

variable "enable_custom_domain" {
  description = "Whether to manage ACM/API custom domain/Route53 resources."
  type        = bool
  default     = false
}

variable "root_domain_name" {
  description = "Root DNS domain used for API custom domain resources (for example: charitystatusapi.com)."
  type        = string
  default     = ""
}

variable "route53_zone_name" {
  description = "Optional Route53 hosted zone name override (for example: charitystatusapi.com.). If empty, root_domain_name is used."
  type        = string
  default     = ""
}

variable "base_name" {
  description = "Base name for resources."
  type        = string
}

variable "enrichment_mock_enabled" {
  description = "Enable deterministic mock enrichment provider."
  type        = bool
  default     = false
}

variable "enrichment_candid_enabled" {
  description = "Enable Candid enrichment provider integration."
  type        = bool
  default     = false
}

variable "enrichment_candid_endpoint" {
  description = "Candid API endpoint URL (if candid provider is enabled)."
  type        = string
  default     = ""
}

variable "enrichment_candid_api_key" {
  description = "Candid API key (if candid provider is enabled)."
  type        = string
  default     = ""
  sensitive   = true
}

variable "enrichment_timeout_seconds" {
  description = "Timeout in seconds for enrichment provider calls."
  type        = number
  default     = 5
}

variable "serving_dynamodb_enabled" {
  description = "Enable DynamoDB materialized profile serving layer."
  type        = bool
  default     = true
}

variable "refresh_lambda_enabled" {
  description = "Enable the materialization refresh Lambda."
  type        = bool
  default     = true
}

variable "refresh_mode" {
  description = "Default refresh mode for materialization updates."
  type        = string
  default     = "refresh_changed"
}

variable "refresh_batch_size" {
  description = "Max EINs processed per refresh invocation."
  type        = number
  default     = 100
}

variable "refresh_force" {
  description = "Force profile writes even when source hash and model version are unchanged."
  type        = bool
  default     = false
}

variable "refresh_source_detection_enabled" {
  description = "Allow source-driven changed-EIN detection when no explicit EIN list is provided."
  type        = bool
  default     = false
}

variable "refresh_schedule_expression" {
  description = "Optional EventBridge schedule expression for the refresh Lambda. Empty disables scheduling."
  type        = string
  default     = ""
}

variable "bootstrap_nonprod_override" {
  description = "Allow bootstrap_all in non-prod when explicitly enabled."
  type        = bool
  default     = false
}

variable "bootstrap_start_after_ein" {
  description = "Optional EIN cursor to resume bootstrap_all processing after this EIN."
  type        = string
  default     = ""
}

variable "bootstrap_max_batches_per_run" {
  description = "Optional limit on bootstrap_all batches processed per invocation; 0 means unlimited."
  type        = number
  default     = 0
}
