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

variable "form990_raw_source_prefix" {
  description = "S3 prefix for raw IRS Form 990 source artifacts (original CSV and ZIP downloads)."
  type        = string
  default     = "form990/raw-sources/"
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

variable "form990_relationships_prefix" {
  description = "S3 prefix for derived Form 990 relationship edge artifacts."
  type        = string
  default     = "form990/normalized/relationships/"
}

variable "form990_index_url" {
  description = "Optional Form 990 IRS index URL used when lambda_form990 is invoked without explicit records."
  type        = string
  default     = ""
}

variable "form990_index_urls" {
  description = "Optional comma-delimited list of Form 990 IRS index URLs for fallback ingestion."
  type        = string
  default     = ""
}

variable "form990_index_fetch_timeout_seconds" {
  description = "Timeout for Form 990 index URL fetches."
  type        = number
  default     = 60
}

variable "form990_default_download_raw" {
  description = "Default raw XML download behavior for Form 990 ingest when download_raw is not explicitly provided."
  type        = bool
  default     = true
}

variable "form990_schedule_expression" {
  description = "Optional EventBridge schedule expression for form990 ingest Lambda. Empty disables scheduling."
  type        = string
  default     = ""
}

variable "form990_run_mode" {
  description = "Default mode for form990 ingestion orchestration: incremental or bootstrap."
  type        = string
  default     = "incremental"
}

variable "form990_batch_size" {
  description = "Batch size for incremental/bootstrap filing processing."
  type        = number
  default     = 100
}

variable "form990_retry_count" {
  description = "Retry count for transient IRS index fetch failures."
  type        = number
  default     = 2
}

variable "form990_source_catalog_json" {
  description = "Optional JSON array describing available IRS Form 990 index sources (year/archive/index_url)."
  type        = string
  default     = ""
}

variable "form990_incremental_year_window" {
  description = "Number of recent years checked during incremental policy mode."
  type        = number
  default     = 2
}

variable "form990_reconciliation_enabled" {
  description = "Enable periodic full reconciliation scans over all discovered years."
  type        = bool
  default     = true
}

variable "form990_reconciliation_cadence_days" {
  description = "Cadence in days for reconciliation scans when reconciliation is enabled."
  type        = number
  default     = 30
}

variable "form990_target_years" {
  description = "Optional comma-delimited explicit target years override for ingest policy."
  type        = string
  default     = ""
}

variable "form990_last_reconciliation_at" {
  description = "Optional ISO timestamp for last successful full reconciliation (policy hint)."
  type        = string
  default     = ""
}

variable "form990_source_mode" {
  description = "Form 990 source discovery mode: static_manifest (repo-backed default), configured (manual index/source_catalog flow), or irs_page (legacy compatibility)."
  type        = string
  default     = "static_manifest"
}

variable "form990_enable_next_year_generation" {
  description = "Allow static Form 990 discovery to synthesize a single next-year TEOS source set from the latest explicit manifest year."
  type        = bool
  default     = true
}

variable "form990_irs_downloads_page_url" {
  description = "IRS Form 990 downloads landing page URL used only when form990_source_mode=irs_page."
  type        = string
  default     = "https://www.irs.gov/charities-non-profits/form-990-series-downloads"
}

variable "form990_zip_fetch_timeout_seconds" {
  description = "Timeout for yearly Form 990 ZIP archive downloads."
  type        = number
  default     = 120
}

variable "form990_zip_max_xml_file_size_bytes" {
  description = "Maximum XML entry size allowed when extracting yearly Form 990 ZIP archives."
  type        = number
  default     = 20971520
}

variable "form990_lambda_timeout_seconds" {
  description = "Timeout for the Form 990 ingest Lambda."
  type        = number
  default     = 900
}

variable "form990_lambda_memory_size_mb" {
  description = "Memory size in MB for the Form 990 ingest Lambda."
  type        = number
  default     = 3072
}

variable "form990_execution_mode" {
  description = "Form 990 execution mode: inline (single invocation) or orchestrated (SQS chunking)."
  type        = string
  default     = "inline"
}

variable "form990_chunk_size" {
  description = "Chunk size for orchestrated Form 990 work items."
  type        = number
  default     = 250
}

variable "form990_worker_timeout_seconds" {
  description = "Timeout for Form 990 worker Lambda."
  type        = number
  default     = 300
}

variable "form990_worker_memory_size_mb" {
  description = "Memory size in MB for Form 990 worker Lambda."
  type        = number
  default     = 1024
}

variable "form990_worker_reserved_concurrency" {
  description = "Reserved concurrency for Form 990 worker Lambda. Set 0 for unreserved."
  type        = number
  default     = 5
}

variable "form990_queue_visibility_timeout_seconds" {
  description = "Visibility timeout for Form 990 SQS work queue."
  type        = number
  default     = 600
}

variable "form990_queue_max_receive_count" {
  description = "Maximum receives before Form 990 work items move to DLQ."
  type        = number
  default     = 3
}

variable "form990_queue_batch_size" {
  description = "SQS event source batch size for Form 990 worker."
  type        = number
  default     = 1
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

variable "enrichment_mock_offered" {
  description = "Whether the deployment offers the deterministic mock enrichment provider."
  type        = bool
  default     = null
  nullable    = true
}

variable "enrichment_candid_enabled" {
  description = "Enable Candid enrichment provider integration."
  type        = bool
  default     = false
}

variable "enrichment_candid_offered" {
  description = "Whether the deployment offers the Candid integration."
  type        = bool
  default     = null
  nullable    = true
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

variable "third_party_integrations_enabled" {
  description = "Master enablement flag for platform-level third-party integration availability."
  type        = bool
  default     = false
}

variable "integration_candid_enabled" {
  description = "Platform-level availability flag for the Candid integration."
  type        = bool
  default     = false
}

variable "integration_candid_client_id" {
  description = "Optional Candid client identifier used by the normalized third-party integration config model."
  type        = string
  default     = ""
}

variable "integration_candid_client_secret" {
  description = "Optional Candid client secret used by the normalized third-party integration config model."
  type        = string
  default     = ""
  sensitive   = true
}

variable "integration_charity_navigator_enabled" {
  description = "Platform-level availability flag for the Charity Navigator integration."
  type        = bool
  default     = false
}

variable "integration_charity_navigator_api_key" {
  description = "Optional Charity Navigator API key used by the normalized third-party integration config model."
  type        = string
  default     = ""
  sensitive   = true
}

variable "default_require_candid_for_evaluation" {
  description = "Default organization-level policy flag for requiring Candid during evaluation."
  type        = bool
  default     = false
}

variable "default_require_charity_navigator_for_evaluation" {
  description = "Default organization-level policy flag for requiring Charity Navigator during evaluation."
  type        = bool
  default     = false
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

variable "batch_verify_max_size" {
  description = "Maximum number of rows accepted by POST /v1/verify/batch."
  type        = number
  default     = 25
}

variable "enrichment_state_registry_enabled" {
  description = "Enable scaffolded state registry compliance provider."
  type        = bool
  default     = false
}

variable "enrichment_state_registry_offered" {
  description = "Whether the deployment offers the state registry integration."
  type        = bool
  default     = null
  nullable    = true
}

variable "enrichment_state_registry_mock_enabled" {
  description = "Enable deterministic mock state registry compliance provider."
  type        = bool
  default     = false
}

variable "enrichment_state_registry_endpoint" {
  description = "Optional endpoint for state registry provider adapter."
  type        = string
  default     = ""
}

variable "enrichment_state_registry_colorado_enabled" {
  description = "Enable the Colorado state registry adapter through the shared state-registry orchestration layer."
  type        = bool
  default     = false
}

variable "enrichment_state_registry_colorado_app_token" {
  description = "Optional Socrata app token for the Colorado state registry dataset."
  type        = string
  default     = ""
}

variable "enrichment_state_registry_kentucky_enabled" {
  description = "Enable the Kentucky state registry adapter through the shared state-registry orchestration layer."
  type        = bool
  default     = false
}

variable "enrichment_state_registry_kentucky_companies_url" {
  description = "Kentucky bulk company snapshot URL used by the shared state-registry orchestration layer."
  type        = string
  default     = ""
}

variable "enrichment_state_business_enabled" {
  description = "Enable scaffolded state business entity provider."
  type        = bool
  default     = false
}

variable "enrichment_state_business_offered" {
  description = "Whether the deployment offers the state business integration."
  type        = bool
  default     = null
  nullable    = true
}

variable "enrichment_state_business_mock_enabled" {
  description = "Enable deterministic mock state business entity provider."
  type        = bool
  default     = false
}

variable "enrichment_state_business_endpoint" {
  description = "Optional endpoint for state business provider adapter."
  type        = string
  default     = ""
}

variable "enrichment_usaspending_enabled" {
  description = "Enable scaffolded USAspending provider."
  type        = bool
  default     = false
}

variable "enrichment_usaspending_offered" {
  description = "Whether the deployment offers the USAspending integration."
  type        = bool
  default     = null
  nullable    = true
}

variable "enrichment_usaspending_mock_enabled" {
  description = "Enable deterministic mock USAspending provider."
  type        = bool
  default     = false
}

variable "enrichment_usaspending_endpoint" {
  description = "Optional endpoint for USAspending provider adapter."
  type        = string
  default     = ""
}

variable "enrichment_ofac_enabled" {
  description = "Enable scaffolded OFAC sanctions provider."
  type        = bool
  default     = false
}

variable "enrichment_ofac_offered" {
  description = "Whether the deployment offers the OFAC integration."
  type        = bool
  default     = null
  nullable    = true
}

variable "enrichment_ofac_mock_enabled" {
  description = "Enable deterministic mock OFAC provider."
  type        = bool
  default     = false
}

variable "enrichment_ofac_endpoint" {
  description = "Optional endpoint for OFAC provider adapter."
  type        = string
  default     = ""
}

variable "search_max_limit" {
  description = "Maximum page size allowed for GET /v1/nonprofits/search."
  type        = number
  default     = 50
}

variable "search_default_limit" {
  description = "Default page size for GET /v1/nonprofits/search."
  type        = number
  default     = 20
}

variable "api_auth_enabled" {
  description = "Enable API key authentication and quota enforcement on query endpoints."
  type        = bool
  default     = false
}

variable "api_key_records_json" {
  description = "JSON array of API key records with key_id/secret_hash/account_id/workspace_id/scopes/plan_id/revoked."
  type        = string
  default     = "[]"
  sensitive   = true
}

variable "oauth_m2m_enabled" {
  description = "Enable OAuth 2.1 style machine-to-machine bearer token authentication alongside API keys."
  type        = bool
  default     = false
}

variable "oauth_token_records_json" {
  description = "JSON array of legacy pre-issued OAuth bearer token records with client_id/token_hash/account_id/workspace_id/scopes/plan_id/revoked."
  type        = string
  default     = "[]"
  sensitive   = true
}

variable "oauth_client_records_json" {
  description = "JSON array of OAuth client credential records with client_id/client_secret_hash/account_id/workspace_id/scopes/plan_id/revoked."
  type        = string
  default     = "[]"
  sensitive   = true
}

variable "oauth_token_ttl_seconds" {
  description = "Lifetime in seconds for OAuth client-credentials access tokens issued by POST /v1/oauth/token."
  type        = number
  default     = 3600
}

variable "admin_key_records_json" {
  description = "JSON array of admin key records with admin_id/secret_hash/revoked for the separate control-plane admin surface."
  type        = string
  default     = "[]"
  sensitive   = true
}

variable "tenant_integration_settings_json" {
  description = "JSON array of tenant/workspace third-party integration settings keyed by workspace_id/account_id."
  type        = string
  default     = "[]"
}

variable "organization_integration_settings_json" {
  description = "JSON array of organization/workspace third-party integration settings keyed by workspace_id/account_id."
  type        = string
  default     = "[]"
}

variable "stripe_billing_enabled" {
  description = "Enable Stripe-hosted billing checkout enrollment endpoints."
  type        = bool
  default     = false
}

variable "stripe_price_ids_json" {
  description = "JSON object mapping paid plan codes to Stripe Price IDs for hosted checkout."
  type        = string
  default     = "{}"
}

variable "stripe_secret_key" {
  description = "Stripe secret API key used for hosted checkout session creation."
  type        = string
  default     = ""
  sensitive   = true
}

variable "stripe_webhook_secret" {
  description = "Stripe webhook signing secret used to verify hosted billing lifecycle callbacks."
  type        = string
  default     = ""
  sensitive   = true
}

variable "free_trial_enabled" {
  description = "Enable free-trial lifecycle activation for eligible organizations."
  type        = bool
  default     = false
}

variable "free_trial_duration_days" {
  description = "Length of the free trial in days once activated."
  type        = number
  default     = 14
}

variable "free_trial_plan_code" {
  description = "Paid-tier entitlement profile granted during an active free trial."
  type        = string
  default     = "growth"
}

variable "free_trial_monthly_request_limit" {
  description = "Optional monthly request cap override for active trials. Null keeps the trial plan default."
  type        = number
  default     = null
  nullable    = true
}

variable "ops_metadata_prefix" {
  description = "S3 prefix for operational ingest/refresh run metadata and diagnostics."
  type        = string
  default     = "ops/"
}
