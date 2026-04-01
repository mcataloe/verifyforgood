variable "aws_region" {
  description = "AWS region for provider operations."
  type        = string
}

variable "environment" {
  description = "Deployment environment (for example: dev, staging, prod)."
  type        = string
}

variable "app_name" {
  description = "Neutral internal application identifier used for runtime metadata such as outbound user-agent strings."
  type        = string
  default     = "verification-platform"
}

variable "public_brand_name" {
  description = "Public-facing product label used when external integrations need a customer-visible brand name."
  type        = string
  default     = "VerifyForGood"
}

variable "support_email" {
  description = "Customer-facing support email exposed by the branding layer for public messaging and support-oriented error responses."
  type        = string
  default     = "support@verifyforgood.com"
}

variable "domain" {
  description = "Customer-facing product domain used by the branding layer. This does not manage Route53 or API custom-domain infrastructure."
  type        = string
  default     = "verifyforgood.com"
}

variable "resource_name_strategy" {
  description = "Physical resource naming mode. Use legacy to preserve existing deployed names; use standardized to opt into <namespace>-<platform>-<purpose>-<environment>-<region>."
  type        = string
  default     = "legacy"

  validation {
    condition     = contains(["legacy", "standardized"], var.resource_name_strategy)
    error_message = "resource_name_strategy must be either legacy or standardized."
  }
}

variable "resource_name_overrides" {
  description = "Optional per-resource physical name overrides keyed by the main.tf resource_names map. Overrides take precedence over both legacy and standardized naming."
  type        = map(string)
  default     = {}
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

variable "monthly_ingest_state_machine_enabled" {
  description = "Enable the Step Functions monthly private-ingest orchestration workflow."
  type        = bool
  default     = false
}

variable "monthly_ingest_schedule_expression" {
  description = "Optional EventBridge schedule expression for the monthly private-ingest state machine. Empty disables the schedule."
  type        = string
  default     = ""
}

variable "monthly_ingest_workflow_basename" {
  description = "Basename for the monthly private-ingest workflow. The environment slug is appended when MONTHLY_INGEST_WORKFLOW_NAME is not explicitly set."
  type        = string
  default     = "monthly-ingest"
}

variable "monthly_ingest_workflow_name" {
  description = "Optional explicit Step Functions workflow name override for monthly private-ingest orchestration."
  type        = string
  default     = ""
}

variable "monthly_ingest_workflow_version" {
  description = "Version string embedded into monthly private-ingest workflow input and runtime metadata."
  type        = string
  default     = "2026-03"
}

variable "monthly_ingest_vpc_id" {
  description = "Existing VPC identifier used for on-demand interface endpoint creation."
  type        = string
  default     = ""
}

variable "api_ecs_enabled" {
  description = "Enable the parallel ECS Fargate API runtime and ALB ingress stack."
  type        = bool
  default     = false
}

variable "api_ecs_vpc_id" {
  description = "Existing VPC identifier used by the ECS API service, ALB, and related security groups."
  type        = string
  default     = ""

  validation {
    condition     = !var.api_ecs_enabled || trim(var.api_ecs_vpc_id, " ") != ""
    error_message = "api_ecs_vpc_id must be set when api_ecs_enabled=true."
  }
}

variable "api_ecs_public_subnet_ids" {
  description = "Existing public subnet identifiers used by the API ALB."
  type        = list(string)
  default     = []

  validation {
    condition     = !var.api_ecs_enabled || length(var.api_ecs_public_subnet_ids) > 0
    error_message = "api_ecs_public_subnet_ids must contain at least one subnet when api_ecs_enabled=true."
  }
}

variable "api_ecs_private_subnet_ids" {
  description = "Existing private subnet identifiers used by the ECS API tasks."
  type        = list(string)
  default     = []

  validation {
    condition     = !var.api_ecs_enabled || length(var.api_ecs_private_subnet_ids) > 0
    error_message = "api_ecs_private_subnet_ids must contain at least one subnet when api_ecs_enabled=true."
  }
}

variable "api_ecs_additional_security_group_ids" {
  description = "Optional additional security groups attached to the ECS API tasks."
  type        = list(string)
  default     = []
}

variable "api_ecs_image_uri" {
  description = "Optional full container image URI for the API service. Empty uses the managed ECR repository plus api_ecs_image_tag."
  type        = string
  default     = ""
}

variable "api_ecs_image_tag" {
  description = "Image tag used with the managed API ECR repository when api_ecs_image_uri is empty."
  type        = string
  default     = "latest"
}

variable "api_ecs_container_name" {
  description = "Container name inside the ECS API task definition."
  type        = string
  default     = "api"
}

variable "api_ecs_container_port" {
  description = "TCP port exposed by the API container and target group."
  type        = number
  default     = 8000
}

variable "api_ecs_task_cpu" {
  description = "CPU units for the managed ECS API task definition."
  type        = number
  default     = 1024
}

variable "api_ecs_task_memory" {
  description = "Memory in MiB for the managed ECS API task definition."
  type        = number
  default     = 2048
}

variable "api_ecs_desired_count" {
  description = "Desired task count for the ECS API service."
  type        = number
  default     = 1
}

variable "api_ecs_log_retention_days" {
  description = "Retention in days for the managed CloudWatch log group used by the ECS API service."
  type        = number
  default     = 30
}

variable "api_ecs_health_check_path" {
  description = "HTTP path used by the ALB target group health check for the ECS API service."
  type        = string
  default     = "/ready"
}

variable "api_ecs_health_check_matcher" {
  description = "Success HTTP status matcher used by the ALB target group health check for the ECS API service."
  type        = string
  default     = "200-399"
}

variable "api_ecs_health_check_interval_seconds" {
  description = "Interval in seconds for the ALB target group health check."
  type        = number
  default     = 30
}

variable "api_ecs_health_check_timeout_seconds" {
  description = "Timeout in seconds for the ALB target group health check."
  type        = number
  default     = 5
}

variable "api_ecs_healthy_threshold" {
  description = "Healthy threshold count for the ALB target group health check."
  type        = number
  default     = 2
}

variable "api_ecs_unhealthy_threshold" {
  description = "Unhealthy threshold count for the ALB target group health check."
  type        = number
  default     = 2
}

variable "api_ecs_health_check_grace_period_seconds" {
  description = "Grace period in seconds before the ECS service applies target group health checks to new API tasks."
  type        = number
  default     = 60
}

variable "api_ecs_target_group_deregistration_delay_seconds" {
  description = "Deregistration delay in seconds for the ECS API target group."
  type        = number
  default     = 30
}

variable "api_alb_certificate_arn" {
  description = "Optional ACM certificate ARN for the API ALB HTTPS listener. Empty reuses the managed custom-domain certificate when available."
  type        = string
  default     = ""
}

variable "api_ecs_secret_arns" {
  description = "Optional Secrets Manager or SSM parameter ARNs keyed by environment variable name for ECS API secret injection."
  type        = map(string)
  default     = {}
}

variable "api_ecs_secret_kms_key_arns" {
  description = "Optional KMS key ARNs used to decrypt entries referenced by api_ecs_secret_arns."
  type        = list(string)
  default     = []
}

variable "api_alb_ssl_policy" {
  description = "SSL policy used by the API ALB HTTPS listener."
  type        = string
  default     = "ELBSecurityPolicy-TLS13-1-2-2021-06"
}

variable "platform_postgres_enabled" {
  description = "Provision and wire the additive PostgreSQL RDS foundation for platform data."
  type        = bool
  default     = false
}

variable "platform_postgres_vpc_id" {
  description = "Existing VPC identifier used by the platform PostgreSQL RDS instance and the query Lambda VPC attachment."
  type        = string
  default     = ""

  validation {
    condition     = !var.platform_postgres_enabled || trim(var.platform_postgres_vpc_id, " ") != ""
    error_message = "platform_postgres_vpc_id must be set when platform_postgres_enabled=true."
  }
}

variable "platform_postgres_private_subnet_ids" {
  description = "Existing private subnet identifiers shared by the platform PostgreSQL RDS instance and the query Lambda VPC attachment."
  type        = list(string)
  default     = []

  validation {
    condition     = !var.platform_postgres_enabled || length(var.platform_postgres_private_subnet_ids) > 0
    error_message = "platform_postgres_private_subnet_ids must contain at least one subnet when platform_postgres_enabled=true."
  }
}

variable "platform_postgres_lambda_additional_security_group_ids" {
  description = "Optional additional security groups attached to the query Lambda when platform PostgreSQL connectivity is enabled."
  type        = list(string)
  default     = []
}

variable "platform_postgres_database_name" {
  description = "Initial PostgreSQL database name for platform/application relational data."
  type        = string
  default     = "verification_platform"
}

variable "platform_postgres_username" {
  description = "Initial PostgreSQL application username when Terraform manages the database secret."
  type        = string
  default     = "platform_app"
}

variable "platform_postgres_port" {
  description = "TCP port for the platform PostgreSQL instance."
  type        = number
  default     = 5432
}

variable "platform_postgres_instance_class" {
  description = "RDS instance class for the platform PostgreSQL instance."
  type        = string
  default     = "db.t4g.micro"
}

variable "platform_postgres_engine_version" {
  description = "Optional explicit PostgreSQL engine version. Empty lets AWS choose the default supported version."
  type        = string
  default     = ""
}

variable "platform_postgres_allocated_storage_gib" {
  description = "Allocated storage in GiB for the platform PostgreSQL instance."
  type        = number
  default     = 20
}

variable "platform_postgres_max_allocated_storage_gib" {
  description = "Maximum autoscaled storage in GiB for the platform PostgreSQL instance."
  type        = number
  default     = 100
}

variable "platform_postgres_backup_retention_days" {
  description = "Optional backup retention in days for the platform PostgreSQL instance. Null defaults to 1 in non-prod and 7 in prod."
  type        = number
  default     = null
  nullable    = true
}

variable "platform_postgres_publicly_accessible" {
  description = "Whether the platform PostgreSQL instance should be publicly accessible."
  type        = bool
  default     = false
}

variable "platform_postgres_deletion_protection_enabled" {
  description = "Optional override for RDS deletion protection. Null defaults to enabled in prod and disabled elsewhere."
  type        = bool
  default     = null
  nullable    = true
}

variable "platform_postgres_skip_final_snapshot" {
  description = "Optional override for skipping the final snapshot on destroy. Null defaults to false in prod and true elsewhere."
  type        = bool
  default     = null
  nullable    = true
}

variable "platform_postgres_existing_secret_arn" {
  description = "Optional existing Secrets Manager secret ARN containing PostgreSQL username/password JSON. Empty lets Terraform manage the secret."
  type        = string
  default     = ""
}

variable "platform_postgres_secret_kms_key_arn" {
  description = "Optional KMS key ARN used to encrypt the managed PostgreSQL Secrets Manager secret."
  type        = string
  default     = ""
}

variable "platform_postgres_sslmode" {
  description = "SSL mode advertised to runtime consumers of the platform PostgreSQL configuration."
  type        = string
  default     = "require"
}

variable "platform_identity_store_backend" {
  description = "Persistence backend for portal identity and customer-account repositories."
  type        = string
  default     = "postgres"

  validation {
    condition     = contains(["dynamodb", "postgres"], var.platform_identity_store_backend)
    error_message = "platform_identity_store_backend must be either dynamodb or postgres."
  }
}

variable "platform_organization_settings_store_backend" {
  description = "Persistence backend for organization settings storage."
  type        = string
  default     = "dynamodb"

  validation {
    condition     = contains(["dynamodb", "postgres"], var.platform_organization_settings_store_backend)
    error_message = "platform_organization_settings_store_backend must be either dynamodb or postgres."
  }
}

variable "platform_control_plane_store_backend" {
  description = "Persistence backend for control-plane and billing storage."
  type        = string
  default     = "dynamodb"

  validation {
    condition     = contains(["dynamodb", "postgres"], var.platform_control_plane_store_backend)
    error_message = "platform_control_plane_store_backend must be either dynamodb or postgres."
  }
}

variable "platform_nonprofit_query_backend" {
  description = "Read backend for nonprofit lookup, search, and filings query paths."
  type        = string
  default     = "athena"

  validation {
    condition     = contains(["athena", "postgres"], var.platform_nonprofit_query_backend)
    error_message = "platform_nonprofit_query_backend must be either athena or postgres."
  }
}

variable "monthly_ingest_private_subnet_ids" {
  description = "Existing private subnet identifiers shared by the ECS task and the temporary interface endpoints."
  type        = list(string)
  default     = []
}

variable "monthly_ingest_endpoint_security_group_ids" {
  description = "Security groups attached to temporary interface endpoints for ECS image pull and logging access."
  type        = list(string)
  default     = []
}

variable "monthly_ingest_task_security_group_ids" {
  description = "Security groups attached to the monthly private-ingest ECS task."
  type        = list(string)
  default     = []
}

variable "monthly_ingest_ecs_cluster_arn" {
  description = "Existing ECS cluster ARN used by the monthly private-ingest RunTask step."
  type        = string
  default     = ""
}

variable "monthly_ingest_ecs_cluster_name" {
  description = "Existing ECS cluster name used for environment metadata and human-readable references. Empty falls back to the centralized resource name alias."
  type        = string
  default     = ""
}

variable "monthly_ingest_task_definition_arn" {
  description = "Existing ECS task definition ARN for the monthly private-ingest worker task. Empty lets Terraform manage the task definition."
  type        = string
  default     = ""
}

variable "monthly_ingest_task_execution_role_arn" {
  description = "Task execution role ARN passed through the Step Functions execution role for ECS RunTask. Empty lets Terraform manage the execution role."
  type        = string
  default     = ""
}

variable "monthly_ingest_task_role_arn" {
  description = "Application task role ARN passed through the Step Functions execution role for ECS RunTask. Empty lets Terraform manage the task role."
  type        = string
  default     = ""
}

variable "monthly_ingest_container_name" {
  description = "Container name inside the ECS task definition that receives the monthly-ingest environment overrides."
  type        = string
  default     = "monthly-ingest"
}

variable "monthly_ingest_worker_image_uri" {
  description = "Optional full container image URI for the monthly private-ingest worker. Empty uses the managed ECR repository plus monthly_ingest_worker_image_tag."
  type        = string
  default     = ""
}

variable "monthly_ingest_worker_image_tag" {
  description = "Image tag used with the managed monthly private-ingest worker ECR repository when monthly_ingest_worker_image_uri is empty."
  type        = string
  default     = "latest"
}

variable "monthly_ingest_task_cpu" {
  description = "CPU units for the managed monthly private-ingest ECS task definition."
  type        = number
  default     = 2048
}

variable "monthly_ingest_task_memory" {
  description = "Memory in MiB for the managed monthly private-ingest ECS task definition."
  type        = number
  default     = 8192
}

variable "monthly_ingest_task_ephemeral_storage_gib" {
  description = "Ephemeral storage in GiB for the managed monthly private-ingest ECS task definition."
  type        = number
  default     = 100
}

variable "monthly_ingest_task_log_retention_days" {
  description = "Retention in days for the managed CloudWatch log group used by the monthly private-ingest ECS task."
  type        = number
  default     = 30
}

variable "monthly_ingest_task_allowed_bucket_arns" {
  description = "Additional S3 bucket ARNs the managed monthly private-ingest ECS task role may access for source or destination objects."
  type        = list(string)
  default     = []
}

variable "monthly_ingest_staging_lambda_arn" {
  description = "Optional external staging Lambda ARN invoked before ECS processing when skip_staging=false. Empty lets Terraform create and wire the in-repo staging Lambda."
  type        = string
  default     = ""
}

variable "monthly_ingest_schedule_source_bucket" {
  description = "Optional source bucket passed by the monthly private-ingest EventBridge schedule."
  type        = string
  default     = ""
}

variable "monthly_ingest_schedule_source_key" {
  description = "Optional pre-staged source key passed by the monthly private-ingest EventBridge schedule. When empty and skip_staging=false, the schedule uses an internal placeholder until the staging Lambda returns the real key."
  type        = string
  default     = ""
}

variable "monthly_ingest_schedule_destination_bucket" {
  description = "Optional destination bucket passed by the monthly private-ingest EventBridge schedule."
  type        = string
  default     = ""
}

variable "monthly_ingest_schedule_destination_prefix" {
  description = "Optional destination prefix passed by the monthly private-ingest EventBridge schedule."
  type        = string
  default     = ""
}

variable "monthly_ingest_schedule_job_id" {
  description = "Optional job identifier used by the monthly private-ingest EventBridge schedule input."
  type        = string
  default     = ""
}

variable "monthly_ingest_schedule_correlation_id" {
  description = "Optional correlation identifier used by the monthly private-ingest EventBridge schedule input. Empty falls back to monthly_ingest_schedule_job_id."
  type        = string
  default     = ""
}

variable "monthly_ingest_schedule_skip_staging" {
  description = "Whether the EventBridge schedule should bypass the staging Lambda and assume the source key already exists in S3."
  type        = bool
  default     = false
}

variable "monthly_ingest_schedule_context_json" {
  description = "Optional JSON object passed as schedule_context in the monthly private-ingest EventBridge schedule input. This is the preferred place to supply upstream ZIP metadata such as source_url, source_year, source_archive_key, source_filename, and source_timestamp."
  type        = string
  default     = "{}"
}

variable "monthly_ingest_endpoint_poll_interval_seconds" {
  description = "Polling interval in seconds while waiting for temporary interface endpoints to become available."
  type        = number
  default     = 20
}

variable "monthly_ingest_endpoint_ready_max_attempts" {
  description = "Maximum readiness polls for each temporary interface endpoint before the workflow fails and starts cleanup."
  type        = number
  default     = 30
}

variable "monthly_ingest_retry_interval_seconds" {
  description = "Base retry interval for transient Step Functions AWS service task failures in the monthly private-ingest workflow."
  type        = number
  default     = 2
}

variable "monthly_ingest_retry_max_attempts" {
  description = "Maximum transient retry attempts per AWS service task in the monthly private-ingest workflow."
  type        = number
  default     = 3
}

variable "monthly_ingest_retry_backoff_rate" {
  description = "Exponential backoff rate for transient Step Functions AWS service task retries in the monthly private-ingest workflow."
  type        = number
  default     = 2
}

variable "monthly_ingest_staging_lambda_timeout_seconds" {
  description = "Timeout in seconds for the staging Lambda Step Functions task."
  type        = number
  default     = 900
}

variable "monthly_ingest_ecs_task_timeout_seconds" {
  description = "Timeout in seconds for the ECS RunTask.sync step."
  type        = number
  default     = 14400
}

variable "monthly_ingest_state_machine_timeout_seconds" {
  description = "Overall timeout in seconds for the monthly private-ingest Step Functions state machine."
  type        = number
  default     = 21600
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
  description = "Legacy Athena workgroup base name used when resource_name_strategy=legacy."
  type        = string
  default     = "irs-eo-bmf"
}

variable "enable_custom_domain" {
  description = "Whether to manage ACM/API custom domain/Route53 resources."
  type        = bool
  default     = false
}

variable "root_domain_name" {
  description = "Root DNS domain used for API custom domain resources (for example: verification.example.com)."
  type        = string
  default     = ""
}

variable "route53_zone_name" {
  description = "Optional Route53 hosted zone name override (for example: verification.example.com.). If empty, root_domain_name is used."
  type        = string
  default     = ""
}

variable "base_name" {
  description = "Legacy brand-derived base name used when resource_name_strategy=legacy."
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

variable "cors_allowed_origins" {
  description = "Explicit browser Origin allowlist for API CORS responses."
  type        = list(string)
  default     = []
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
