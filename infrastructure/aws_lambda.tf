#############################################
# LAMBDA - IRS DATA INGESTION
#############################################

locals {
  ingest_package_dir   = "${path.module}/build/ingest_package"
  ingest_package_files = can(fileset(local.ingest_package_dir, "**")) ? fileset(local.ingest_package_dir, "**") : []
  use_ingest_build_dir = length(local.ingest_package_files) > 0
}

data "archive_file" "ingest_zip_from_dir" {
  count       = local.use_ingest_build_dir ? 1 : 0
  type        = "zip"
  source_dir  = local.ingest_package_dir
  output_path = "${path.module}/ingest.zip"
}

data "archive_file" "ingest_zip_from_file" {
  count      = local.use_ingest_build_dir ? 0 : 1
  type       = "zip"
  source_dir = path.module
  excludes = [
    ".terraform/**",
    "build/**",
    "__pycache__/**",
    "terraform.tfstate",
    "terraform.tfstate.*",
    ".terraform.tfstate.lock.info",
    "charity_status/form990/**",
    "charity_status/query/**",
    "charity_status/normalization/**",
    "charity_status/scoring/**",
    "charity_status/api/**",
    "charity_status/future/**",
    "lambda_query.py",
    "lambda_form990.py",
    "ingest.zip",
    "query.zip",
    "form990.zip",
    "*.tf",
    "*.tfvars",
    "*.hcl",
    "*.ps1",
    "requirements*.txt",
  ]
  output_path = "${path.module}/ingest.zip"
}

resource "aws_lambda_function" "ingest" {
  function_name = "irs_dataset_ingest"
  handler       = "lambda_ingest.handler"
  runtime       = "python3.11"
  role          = aws_iam_role.lambda_role.arn
  timeout       = 300
  memory_size   = 1024

  filename         = local.use_ingest_build_dir ? data.archive_file.ingest_zip_from_dir[0].output_path : data.archive_file.ingest_zip_from_file[0].output_path
  source_code_hash = local.use_ingest_build_dir ? data.archive_file.ingest_zip_from_dir[0].output_base64sha256 : data.archive_file.ingest_zip_from_file[0].output_base64sha256

  environment {
    variables = {
      BUCKET = aws_s3_bucket.irs_data.bucket
      PREFIX = local.source_data_prefix_normalized
    }
  }
}

#############################################
# LAMBDA QUERY FUNCTION
#############################################

data "archive_file" "query_zip" {
  type        = "zip"
  source_dir  = path.module
  output_path = "${path.module}/query.zip"
  excludes = [
    ".terraform/**",
    "build/**",
    "__pycache__/**",
    "terraform.tfstate",
    "terraform.tfstate.*",
    ".terraform.tfstate.lock.info",
    "charity_status/ingest/**",
    "charity_status/form990/**",
    "charity_status/future/**",
    "ingest.zip",
    "query.zip",
    "form990.zip",
    "lambda_ingest.py",
    "lambda_form990.py",
    "*.tf",
    "*.tfvars",
    "*.hcl",
    "*.ps1",
    "requirements*.txt",
  ]
}

resource "aws_lambda_function" "query" {
  function_name = "irs_query_api"
  handler       = "lambda_query.handler"
  runtime       = "python3.11"
  role          = aws_iam_role.lambda_role.arn
  timeout       = 30

  filename         = data.archive_file.query_zip.output_path
  source_code_hash = data.archive_file.query_zip.output_base64sha256

  environment {
    variables = {
      DATABASE                                         = aws_glue_catalog_database.eo_bmf.name
      TABLE                                            = aws_glue_catalog_table.eo_bmf.name
      WORKGROUP                                        = aws_athena_workgroup.eo_bmf.name
      FORM990_FILINGS_TABLE                            = aws_glue_catalog_table.form990_metadata.name
      FORM990_METRICS_TABLE                            = aws_glue_catalog_table.form990_metrics.name
      FORM990_GOVERNANCE_TABLE                         = aws_glue_catalog_table.form990_governance.name
      FORM990_QUALITY_TABLE                            = aws_glue_catalog_table.form990_quality.name
      THIRD_PARTY_INTEGRATIONS_ENABLED                 = tostring(var.third_party_integrations_enabled)
      INTEGRATION_CANDID_ENABLED                       = tostring(var.integration_candid_enabled)
      INTEGRATION_CANDID_CLIENT_ID                     = var.integration_candid_client_id
      INTEGRATION_CANDID_CLIENT_SECRET                 = var.integration_candid_client_secret
      INTEGRATION_CHARITY_NAVIGATOR_ENABLED            = tostring(var.integration_charity_navigator_enabled)
      INTEGRATION_CHARITY_NAVIGATOR_API_KEY            = var.integration_charity_navigator_api_key
      DEFAULT_REQUIRE_CANDID_FOR_EVALUATION            = tostring(var.default_require_candid_for_evaluation)
      DEFAULT_REQUIRE_CHARITY_NAVIGATOR_FOR_EVALUATION = tostring(var.default_require_charity_navigator_for_evaluation)
      ENRICHMENT_MOCK_OFFERED                          = tostring(var.enrichment_mock_offered != null ? var.enrichment_mock_offered : var.enrichment_mock_enabled)
      ENRICHMENT_MOCK_ENABLED                          = tostring(var.enrichment_mock_enabled)
      ENRICHMENT_CANDID_OFFERED                        = tostring(var.enrichment_candid_offered != null ? var.enrichment_candid_offered : var.enrichment_candid_enabled)
      ENRICHMENT_CANDID_ENABLED                        = tostring(var.enrichment_candid_enabled)
      ENRICHMENT_CANDID_ENDPOINT                       = var.enrichment_candid_endpoint
      ENRICHMENT_CANDID_API_KEY                        = var.enrichment_candid_api_key
      ENRICHMENT_TIMEOUT_SECONDS                       = tostring(var.enrichment_timeout_seconds)
      ENRICHMENT_STATE_REGISTRY_OFFERED                = tostring(var.enrichment_state_registry_offered != null ? var.enrichment_state_registry_offered : (var.enrichment_state_registry_enabled || var.enrichment_state_registry_mock_enabled))
      ENRICHMENT_STATE_REGISTRY_ENABLED                = tostring(var.enrichment_state_registry_enabled)
      ENRICHMENT_STATE_REGISTRY_MOCK_ENABLED           = tostring(var.enrichment_state_registry_mock_enabled)
      ENRICHMENT_STATE_REGISTRY_ENDPOINT               = var.enrichment_state_registry_endpoint
      ENRICHMENT_STATE_REGISTRY_COLORADO_ENABLED       = tostring(var.enrichment_state_registry_colorado_enabled)
      ENRICHMENT_STATE_REGISTRY_COLORADO_APP_TOKEN     = var.enrichment_state_registry_colorado_app_token
      ENRICHMENT_STATE_REGISTRY_KENTUCKY_ENABLED       = tostring(var.enrichment_state_registry_kentucky_enabled)
      ENRICHMENT_STATE_REGISTRY_KENTUCKY_COMPANIES_URL = var.enrichment_state_registry_kentucky_companies_url
      ENRICHMENT_STATE_BUSINESS_OFFERED                = tostring(var.enrichment_state_business_offered != null ? var.enrichment_state_business_offered : (var.enrichment_state_business_enabled || var.enrichment_state_business_mock_enabled))
      ENRICHMENT_STATE_BUSINESS_ENABLED                = tostring(var.enrichment_state_business_enabled)
      ENRICHMENT_STATE_BUSINESS_MOCK_ENABLED           = tostring(var.enrichment_state_business_mock_enabled)
      ENRICHMENT_STATE_BUSINESS_ENDPOINT               = var.enrichment_state_business_endpoint
      ENRICHMENT_USASPENDING_OFFERED                   = tostring(var.enrichment_usaspending_offered != null ? var.enrichment_usaspending_offered : (var.enrichment_usaspending_enabled || var.enrichment_usaspending_mock_enabled))
      ENRICHMENT_USASPENDING_ENABLED                   = tostring(var.enrichment_usaspending_enabled)
      ENRICHMENT_USASPENDING_MOCK_ENABLED              = tostring(var.enrichment_usaspending_mock_enabled)
      ENRICHMENT_USASPENDING_ENDPOINT                  = var.enrichment_usaspending_endpoint
      ENRICHMENT_OFAC_OFFERED                          = tostring(var.enrichment_ofac_offered != null ? var.enrichment_ofac_offered : (var.enrichment_ofac_enabled || var.enrichment_ofac_mock_enabled))
      ENRICHMENT_OFAC_ENABLED                          = tostring(var.enrichment_ofac_enabled)
      ENRICHMENT_OFAC_MOCK_ENABLED                     = tostring(var.enrichment_ofac_mock_enabled)
      ENRICHMENT_OFAC_ENDPOINT                         = var.enrichment_ofac_endpoint
      PROFILE_TABLE_NAME                               = aws_dynamodb_table.profiles.name
      APP_ENV                                          = var.environment
      SERVING_DDB_ENABLED                              = tostring(var.serving_dynamodb_enabled)
      BATCH_VERIFY_MAX_SIZE                            = tostring(var.batch_verify_max_size)
      SEARCH_MAX_LIMIT                                 = tostring(var.search_max_limit)
      SEARCH_DEFAULT_LIMIT                             = tostring(var.search_default_limit)
      API_AUTH_ENABLED                                 = tostring(var.api_auth_enabled)
      API_KEY_RECORDS_JSON                             = var.api_key_records_json
      OAUTH_M2M_ENABLED                                = tostring(var.oauth_m2m_enabled)
      OAUTH_TOKEN_RECORDS_JSON                         = var.oauth_token_records_json
      OAUTH_CLIENT_RECORDS_JSON                        = var.oauth_client_records_json
      OAUTH_TOKEN_TTL_SECONDS                          = tostring(var.oauth_token_ttl_seconds)
      ORGANIZATION_INTEGRATION_SETTINGS_JSON           = var.organization_integration_settings_json
      TENANT_INTEGRATION_SETTINGS_JSON                 = var.tenant_integration_settings_json
      ORGANIZATION_SETTINGS_TABLE_NAME                 = aws_dynamodb_table.organization_settings.name
      OPS_METADATA_BUCKET                              = aws_s3_bucket.irs_data.bucket
      OPS_METADATA_PREFIX                              = var.ops_metadata_prefix
    }
  }
}

#############################################
# LAMBDA - MATERIALIZATION REFRESH
#############################################

data "archive_file" "refresh_zip" {
  count       = var.refresh_lambda_enabled ? 1 : 0
  type        = "zip"
  source_dir  = path.module
  output_path = "${path.module}/refresh.zip"
  excludes = [
    ".terraform/**",
    "build/**",
    "__pycache__/**",
    "terraform.tfstate",
    "terraform.tfstate.*",
    ".terraform.tfstate.lock.info",
    "charity_status/ingest/**",
    "charity_status/future/**",
    "lambda_ingest.py",
    "lambda_query.py",
    "lambda_form990.py",
    "ingest.zip",
    "query.zip",
    "form990.zip",
    "refresh.zip",
    "*.tf",
    "*.tfvars",
    "*.hcl",
    "*.ps1",
    "requirements*.txt",
  ]
}

resource "aws_lambda_function" "refresh" {
  count         = var.refresh_lambda_enabled ? 1 : 0
  function_name = "irs_profile_refresh"
  handler       = "lambda_refresh.handler"
  runtime       = "python3.11"
  role          = aws_iam_role.lambda_role.arn
  timeout       = 120
  memory_size   = 1024

  filename         = data.archive_file.refresh_zip[0].output_path
  source_code_hash = data.archive_file.refresh_zip[0].output_base64sha256

  environment {
    variables = {
      DATABASE                                         = aws_glue_catalog_database.eo_bmf.name
      TABLE                                            = aws_glue_catalog_table.eo_bmf.name
      WORKGROUP                                        = aws_athena_workgroup.eo_bmf.name
      FORM990_FILINGS_TABLE                            = aws_glue_catalog_table.form990_metadata.name
      FORM990_METRICS_TABLE                            = aws_glue_catalog_table.form990_metrics.name
      FORM990_GOVERNANCE_TABLE                         = aws_glue_catalog_table.form990_governance.name
      FORM990_QUALITY_TABLE                            = aws_glue_catalog_table.form990_quality.name
      THIRD_PARTY_INTEGRATIONS_ENABLED                 = tostring(var.third_party_integrations_enabled)
      INTEGRATION_CANDID_ENABLED                       = tostring(var.integration_candid_enabled)
      INTEGRATION_CANDID_CLIENT_ID                     = var.integration_candid_client_id
      INTEGRATION_CANDID_CLIENT_SECRET                 = var.integration_candid_client_secret
      INTEGRATION_CHARITY_NAVIGATOR_ENABLED            = tostring(var.integration_charity_navigator_enabled)
      INTEGRATION_CHARITY_NAVIGATOR_API_KEY            = var.integration_charity_navigator_api_key
      DEFAULT_REQUIRE_CANDID_FOR_EVALUATION            = tostring(var.default_require_candid_for_evaluation)
      DEFAULT_REQUIRE_CHARITY_NAVIGATOR_FOR_EVALUATION = tostring(var.default_require_charity_navigator_for_evaluation)
      ENRICHMENT_MOCK_OFFERED                          = tostring(var.enrichment_mock_offered != null ? var.enrichment_mock_offered : var.enrichment_mock_enabled)
      ENRICHMENT_MOCK_ENABLED                          = tostring(var.enrichment_mock_enabled)
      ENRICHMENT_CANDID_OFFERED                        = tostring(var.enrichment_candid_offered != null ? var.enrichment_candid_offered : var.enrichment_candid_enabled)
      ENRICHMENT_CANDID_ENABLED                        = tostring(var.enrichment_candid_enabled)
      ENRICHMENT_CANDID_ENDPOINT                       = var.enrichment_candid_endpoint
      ENRICHMENT_CANDID_API_KEY                        = var.enrichment_candid_api_key
      ENRICHMENT_TIMEOUT_SECONDS                       = tostring(var.enrichment_timeout_seconds)
      ENRICHMENT_STATE_REGISTRY_OFFERED                = tostring(var.enrichment_state_registry_offered != null ? var.enrichment_state_registry_offered : (var.enrichment_state_registry_enabled || var.enrichment_state_registry_mock_enabled))
      ENRICHMENT_STATE_REGISTRY_ENABLED                = tostring(var.enrichment_state_registry_enabled)
      ENRICHMENT_STATE_REGISTRY_MOCK_ENABLED           = tostring(var.enrichment_state_registry_mock_enabled)
      ENRICHMENT_STATE_REGISTRY_ENDPOINT               = var.enrichment_state_registry_endpoint
      ENRICHMENT_STATE_REGISTRY_COLORADO_ENABLED       = tostring(var.enrichment_state_registry_colorado_enabled)
      ENRICHMENT_STATE_REGISTRY_COLORADO_APP_TOKEN     = var.enrichment_state_registry_colorado_app_token
      ENRICHMENT_STATE_REGISTRY_KENTUCKY_ENABLED       = tostring(var.enrichment_state_registry_kentucky_enabled)
      ENRICHMENT_STATE_REGISTRY_KENTUCKY_COMPANIES_URL = var.enrichment_state_registry_kentucky_companies_url
      ENRICHMENT_STATE_BUSINESS_OFFERED                = tostring(var.enrichment_state_business_offered != null ? var.enrichment_state_business_offered : (var.enrichment_state_business_enabled || var.enrichment_state_business_mock_enabled))
      ENRICHMENT_STATE_BUSINESS_ENABLED                = tostring(var.enrichment_state_business_enabled)
      ENRICHMENT_STATE_BUSINESS_MOCK_ENABLED           = tostring(var.enrichment_state_business_mock_enabled)
      ENRICHMENT_STATE_BUSINESS_ENDPOINT               = var.enrichment_state_business_endpoint
      ENRICHMENT_USASPENDING_OFFERED                   = tostring(var.enrichment_usaspending_offered != null ? var.enrichment_usaspending_offered : (var.enrichment_usaspending_enabled || var.enrichment_usaspending_mock_enabled))
      ENRICHMENT_USASPENDING_ENABLED                   = tostring(var.enrichment_usaspending_enabled)
      ENRICHMENT_USASPENDING_MOCK_ENABLED              = tostring(var.enrichment_usaspending_mock_enabled)
      ENRICHMENT_USASPENDING_ENDPOINT                  = var.enrichment_usaspending_endpoint
      ENRICHMENT_OFAC_OFFERED                          = tostring(var.enrichment_ofac_offered != null ? var.enrichment_ofac_offered : (var.enrichment_ofac_enabled || var.enrichment_ofac_mock_enabled))
      ENRICHMENT_OFAC_ENABLED                          = tostring(var.enrichment_ofac_enabled)
      ENRICHMENT_OFAC_MOCK_ENABLED                     = tostring(var.enrichment_ofac_mock_enabled)
      ENRICHMENT_OFAC_ENDPOINT                         = var.enrichment_ofac_endpoint
      PROFILE_TABLE_NAME                               = aws_dynamodb_table.profiles.name
      APP_ENV                                          = var.environment
      REFRESH_MODE                                     = var.refresh_mode
      REFRESH_BATCH_SIZE                               = tostring(var.refresh_batch_size)
      FORCE_REFRESH                                    = tostring(var.refresh_force)
      REFRESH_SOURCE_DETECTION_ENABLED                 = tostring(var.refresh_source_detection_enabled)
      BOOTSTRAP_NONPROD_OVERRIDE                       = tostring(var.bootstrap_nonprod_override)
      BOOTSTRAP_START_AFTER_EIN                        = var.bootstrap_start_after_ein
      BOOTSTRAP_MAX_BATCHES_PER_RUN                    = tostring(var.bootstrap_max_batches_per_run)
      OPS_METADATA_BUCKET                              = aws_s3_bucket.irs_data.bucket
      OPS_METADATA_PREFIX                              = var.ops_metadata_prefix
    }
  }
}

#############################################
# LAMBDA - FORM 990 INGESTION
#############################################

data "archive_file" "form990_zip" {
  type        = "zip"
  source_dir  = path.module
  output_path = "${path.module}/build/form990.zip"
  excludes = [
    ".terraform/**",
    "build/**",
    "__pycache__/**",
    "terraform.tfstate",
    "terraform.tfstate.*",
    ".terraform.tfstate.lock.info",
    "charity_status/query/**",
    "charity_status/normalization/**",
    "charity_status/scoring/**",
    "charity_status/ingest/**",
    "charity_status/future/**",
    "lambda_ingest.py",
    "lambda_query.py",
    "ingest.zip",
    "query.zip",
    "form990.zip",
    "*.tf",
    "*.tfvars",
    "*.hcl",
    "*.ps1",
    "requirements*.txt",
  ]
}

resource "aws_lambda_function" "form990_ingest" {
  function_name = "irs_form990_ingest"
  handler       = "lambda_form990.handler"
  runtime       = "python3.11"
  role          = aws_iam_role.lambda_role.arn
  timeout       = var.form990_lambda_timeout_seconds
  memory_size   = var.form990_lambda_memory_size_mb

  filename         = data.archive_file.form990_zip.output_path
  source_code_hash = data.archive_file.form990_zip.output_base64sha256

  environment {
    variables = {
      BUCKET                                  = aws_s3_bucket.irs_data.bucket
      FORM990_RAW_PREFIX                      = local.form990_raw_prefix_normalized
      FORM990_RAW_SOURCE_PREFIX               = local.form990_raw_source_prefix_normalized
      FORM990_METADATA_PREFIX                 = local.form990_metadata_prefix_normalized
      FORM990_MANIFEST_PREFIX                 = local.form990_manifest_prefix_normalized
      FORM990_METRICS_PREFIX                  = local.form990_metrics_prefix_normalized
      FORM990_GOVERNANCE_PREFIX               = local.form990_governance_prefix_normalized
      FORM990_QUALITY_PREFIX                  = local.form990_quality_prefix_normalized
      FORM990_RELATIONSHIPS_PREFIX            = local.form990_relationships_prefix_normalized
      FORM990_INDEX_URL                       = var.form990_index_url
      FORM990_INDEX_URLS                      = var.form990_index_urls
      FORM990_INDEX_FETCH_TIMEOUT_SECONDS     = tostring(var.form990_index_fetch_timeout_seconds)
      FORM990_DEFAULT_DOWNLOAD_RAW            = tostring(var.form990_default_download_raw)
      FORM990_RUN_MODE                        = var.form990_run_mode
      FORM990_BATCH_SIZE                      = tostring(var.form990_batch_size)
      FORM990_RETRY_COUNT                     = tostring(var.form990_retry_count)
      FORM990_SOURCE_CATALOG_JSON             = var.form990_source_catalog_json
      FORM990_INCREMENTAL_YEAR_WINDOW         = tostring(var.form990_incremental_year_window)
      FORM990_RECONCILIATION_ENABLED          = tostring(var.form990_reconciliation_enabled)
      FORM990_RECONCILIATION_CADENCE_DAYS     = tostring(var.form990_reconciliation_cadence_days)
      FORM990_TARGET_YEARS                    = var.form990_target_years
      FORM990_LAST_RECONCILIATION_AT          = var.form990_last_reconciliation_at
      FORM990_SOURCE_MODE                     = var.form990_source_mode
      FORM990_ENABLE_NEXT_YEAR_GENERATION     = tostring(var.form990_enable_next_year_generation)
      FORM990_IRS_DOWNLOADS_PAGE_URL          = var.form990_irs_downloads_page_url
      FORM990_SOURCE_DOWNLOAD_TIMEOUT_SECONDS = tostring(var.form990_zip_fetch_timeout_seconds)
      FORM990_ZIP_FETCH_TIMEOUT_SECONDS       = tostring(var.form990_zip_fetch_timeout_seconds)
      FORM990_ZIP_MAX_XML_FILE_SIZE_BYTES     = tostring(var.form990_zip_max_xml_file_size_bytes)
      FORM990_EXECUTION_MODE                  = "inline"
      FORM990_CHUNK_SIZE                      = tostring(var.form990_chunk_size)
      OPS_METADATA_BUCKET                     = aws_s3_bucket.irs_data.bucket
      OPS_METADATA_PREFIX                     = var.ops_metadata_prefix
    }
  }
}

resource "aws_sqs_queue" "form990_work_dlq" {
  name                      = "irs-form990-work-dlq"
  message_retention_seconds = 1209600
}

resource "aws_sqs_queue" "form990_work_queue" {
  name                       = "irs-form990-work-queue"
  visibility_timeout_seconds = var.form990_queue_visibility_timeout_seconds
  message_retention_seconds  = 345600
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.form990_work_dlq.arn
    maxReceiveCount     = var.form990_queue_max_receive_count
  })
}

resource "aws_lambda_function" "form990_orchestrator" {
  function_name = "irs_form990_orchestrator"
  handler       = "lambda_form990_orchestrator.handler"
  runtime       = "python3.11"
  role          = aws_iam_role.lambda_role.arn
  timeout       = var.form990_lambda_timeout_seconds
  memory_size   = var.form990_lambda_memory_size_mb

  filename         = data.archive_file.form990_zip.output_path
  source_code_hash = data.archive_file.form990_zip.output_base64sha256

  environment {
    variables = {
      BUCKET                                  = aws_s3_bucket.irs_data.bucket
      FORM990_RAW_PREFIX                      = local.form990_raw_prefix_normalized
      FORM990_RAW_SOURCE_PREFIX               = local.form990_raw_source_prefix_normalized
      FORM990_METADATA_PREFIX                 = local.form990_metadata_prefix_normalized
      FORM990_MANIFEST_PREFIX                 = local.form990_manifest_prefix_normalized
      FORM990_METRICS_PREFIX                  = local.form990_metrics_prefix_normalized
      FORM990_GOVERNANCE_PREFIX               = local.form990_governance_prefix_normalized
      FORM990_QUALITY_PREFIX                  = local.form990_quality_prefix_normalized
      FORM990_RELATIONSHIPS_PREFIX            = local.form990_relationships_prefix_normalized
      FORM990_INDEX_URL                       = var.form990_index_url
      FORM990_INDEX_URLS                      = var.form990_index_urls
      FORM990_INDEX_FETCH_TIMEOUT_SECONDS     = tostring(var.form990_index_fetch_timeout_seconds)
      FORM990_DEFAULT_DOWNLOAD_RAW            = tostring(var.form990_default_download_raw)
      FORM990_RUN_MODE                        = var.form990_run_mode
      FORM990_BATCH_SIZE                      = tostring(var.form990_batch_size)
      FORM990_RETRY_COUNT                     = tostring(var.form990_retry_count)
      FORM990_SOURCE_CATALOG_JSON             = var.form990_source_catalog_json
      FORM990_INCREMENTAL_YEAR_WINDOW         = tostring(var.form990_incremental_year_window)
      FORM990_RECONCILIATION_ENABLED          = tostring(var.form990_reconciliation_enabled)
      FORM990_RECONCILIATION_CADENCE_DAYS     = tostring(var.form990_reconciliation_cadence_days)
      FORM990_TARGET_YEARS                    = var.form990_target_years
      FORM990_LAST_RECONCILIATION_AT          = var.form990_last_reconciliation_at
      FORM990_SOURCE_MODE                     = var.form990_source_mode
      FORM990_ENABLE_NEXT_YEAR_GENERATION     = tostring(var.form990_enable_next_year_generation)
      FORM990_IRS_DOWNLOADS_PAGE_URL          = var.form990_irs_downloads_page_url
      FORM990_SOURCE_DOWNLOAD_TIMEOUT_SECONDS = tostring(var.form990_zip_fetch_timeout_seconds)
      FORM990_ZIP_FETCH_TIMEOUT_SECONDS       = tostring(var.form990_zip_fetch_timeout_seconds)
      FORM990_ZIP_MAX_XML_FILE_SIZE_BYTES     = tostring(var.form990_zip_max_xml_file_size_bytes)
      FORM990_EXECUTION_MODE                  = var.form990_execution_mode
      FORM990_CHUNK_SIZE                      = tostring(var.form990_chunk_size)
      FORM990_WORK_QUEUE_URL                  = aws_sqs_queue.form990_work_queue.url
      OPS_METADATA_BUCKET                     = aws_s3_bucket.irs_data.bucket
      OPS_METADATA_PREFIX                     = var.ops_metadata_prefix
    }
  }
}

resource "aws_lambda_function" "form990_worker" {
  function_name                  = "irs_form990_worker"
  handler                        = "lambda_form990_worker.handler"
  runtime                        = "python3.11"
  role                           = aws_iam_role.lambda_role.arn
  timeout                        = var.form990_worker_timeout_seconds
  memory_size                    = var.form990_worker_memory_size_mb
  reserved_concurrent_executions = var.form990_worker_reserved_concurrency > 0 ? var.form990_worker_reserved_concurrency : null

  filename         = data.archive_file.form990_zip.output_path
  source_code_hash = data.archive_file.form990_zip.output_base64sha256

  environment {
    variables = {
      BUCKET                                  = aws_s3_bucket.irs_data.bucket
      FORM990_RAW_PREFIX                      = local.form990_raw_prefix_normalized
      FORM990_RAW_SOURCE_PREFIX               = local.form990_raw_source_prefix_normalized
      FORM990_METADATA_PREFIX                 = local.form990_metadata_prefix_normalized
      FORM990_MANIFEST_PREFIX                 = local.form990_manifest_prefix_normalized
      FORM990_METRICS_PREFIX                  = local.form990_metrics_prefix_normalized
      FORM990_GOVERNANCE_PREFIX               = local.form990_governance_prefix_normalized
      FORM990_QUALITY_PREFIX                  = local.form990_quality_prefix_normalized
      FORM990_RELATIONSHIPS_PREFIX            = local.form990_relationships_prefix_normalized
      FORM990_SOURCE_DOWNLOAD_TIMEOUT_SECONDS = tostring(var.form990_zip_fetch_timeout_seconds)
      OPS_METADATA_BUCKET                     = aws_s3_bucket.irs_data.bucket
      OPS_METADATA_PREFIX                     = var.ops_metadata_prefix
    }
  }
}

resource "aws_lambda_event_source_mapping" "form990_worker_sqs" {
  event_source_arn = aws_sqs_queue.form990_work_queue.arn
  function_name    = aws_lambda_function.form990_worker.arn
  batch_size       = var.form990_queue_batch_size
}


#############################################
# DAILY SCHEDULE (EVENTBRIDGE)
#############################################

resource "aws_cloudwatch_event_rule" "daily_ingest" {
  schedule_expression = "cron(0 3 * * ? *)"
}

resource "aws_cloudwatch_event_target" "lambda_ingest_target" {
  rule      = aws_cloudwatch_event_rule.daily_ingest.name
  target_id = "ingest"
  arn       = aws_lambda_function.ingest.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingest.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_ingest.arn
}

resource "aws_cloudwatch_event_rule" "refresh_schedule" {
  count               = var.refresh_lambda_enabled && trim(var.refresh_schedule_expression, " ") != "" ? 1 : 0
  schedule_expression = var.refresh_schedule_expression
}

resource "aws_cloudwatch_event_target" "refresh_lambda_target" {
  count     = var.refresh_lambda_enabled && trim(var.refresh_schedule_expression, " ") != "" ? 1 : 0
  rule      = aws_cloudwatch_event_rule.refresh_schedule[0].name
  target_id = "refresh"
  arn       = aws_lambda_function.refresh[0].arn
}

resource "aws_lambda_permission" "allow_eventbridge_refresh" {
  count         = var.refresh_lambda_enabled && trim(var.refresh_schedule_expression, " ") != "" ? 1 : 0
  statement_id  = "AllowEventBridgeRefresh"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.refresh[0].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.refresh_schedule[0].arn
}

resource "aws_cloudwatch_event_rule" "form990_schedule" {
  count               = trim(var.form990_schedule_expression, " ") != "" ? 1 : 0
  schedule_expression = var.form990_schedule_expression
}

resource "aws_cloudwatch_event_target" "form990_lambda_target" {
  count     = trim(var.form990_schedule_expression, " ") != "" && var.form990_execution_mode == "inline" ? 1 : 0
  rule      = aws_cloudwatch_event_rule.form990_schedule[0].name
  target_id = "form990-ingest"
  arn       = aws_lambda_function.form990_ingest.arn
}

resource "aws_cloudwatch_event_target" "form990_orchestrator_target" {
  count     = trim(var.form990_schedule_expression, " ") != "" && var.form990_execution_mode == "orchestrated" ? 1 : 0
  rule      = aws_cloudwatch_event_rule.form990_schedule[0].name
  target_id = "form990-orchestrator"
  arn       = aws_lambda_function.form990_orchestrator.arn
}

resource "aws_lambda_permission" "allow_eventbridge_form990" {
  count         = trim(var.form990_schedule_expression, " ") != "" && var.form990_execution_mode == "inline" ? 1 : 0
  statement_id  = "AllowEventBridgeForm990"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.form990_ingest.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.form990_schedule[0].arn
}

resource "aws_lambda_permission" "allow_eventbridge_form990_orchestrator" {
  count         = trim(var.form990_schedule_expression, " ") != "" && var.form990_execution_mode == "orchestrated" ? 1 : 0
  statement_id  = "AllowEventBridgeForm990Orchestrator"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.form990_orchestrator.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.form990_schedule[0].arn
}
