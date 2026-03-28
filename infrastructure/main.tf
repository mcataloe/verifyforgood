locals {
  # Standardized infrastructure names use <namespace>-<platform>-<purpose>-<environment>-<region>
  # so resource identity stays stable across public-brand changes.
  namespace        = "n8x4"
  platform         = "verification"
  region_short     = "use1"
  environment_slug = lower(var.environment)

  domain_name = var.root_domain_name != "" ? var.root_domain_name : "${var.base_name}.com"
  # Compatibility alias: physical resource names can stay pinned to legacy prefixes even while
  # internal identifiers adopt capability-oriented labels.
  stable_resource_prefix                  = local.environment_slug == "prod" ? var.base_name : "${var.base_name}-${local.environment_slug}"
  legacy_name_prefix                      = local.stable_resource_prefix
  data_catalog_prefix                     = replace(local.stable_resource_prefix, "-", "_")
  db_prefix                               = local.data_catalog_prefix
  source_data_prefix_normalized           = "${trim(var.source_data_prefix, "/")}/"
  form990_raw_source_prefix_normalized    = "${trim(var.form990_raw_source_prefix, "/")}/"
  form990_raw_prefix_normalized           = "${trim(var.form990_raw_prefix, "/")}/"
  form990_metadata_prefix_normalized      = "${trim(var.form990_metadata_prefix, "/")}/"
  form990_manifest_prefix_normalized      = "${trim(var.form990_manifest_prefix, "/")}/"
  form990_metrics_prefix_normalized       = "${trim(var.form990_metrics_prefix, "/")}/"
  form990_governance_prefix_normalized    = "${trim(var.form990_governance_prefix, "/")}/"
  form990_quality_prefix_normalized       = "${trim(var.form990_quality_prefix, "/")}/"
  form990_relationships_prefix_normalized = "${trim(var.form990_relationships_prefix, "/")}/"

  standardized_resource_names = {
    source_data_bucket                = "${local.namespace}-${local.platform}-irs-source-data-bucket-${local.environment_slug}-${local.region_short}"
    athena_results_bucket             = "${local.namespace}-${local.platform}-athena-results-${local.environment_slug}-${local.region_short}"
    ecs_cluster                       = "${local.namespace}-${local.platform}-platform-processing-${local.environment_slug}-${local.region_short}"
    profile_table                     = "${local.namespace}-${local.platform}-profiles-${local.environment_slug}-${local.region_short}"
    identity_table                    = "${local.namespace}-${local.platform}-identity-${local.environment_slug}-${local.region_short}"
    organization_settings_table       = "${local.namespace}-${local.platform}-organization-settings-${local.environment_slug}-${local.region_short}"
    control_plane_table               = "${local.namespace}-${local.platform}-control-plane-${local.environment_slug}-${local.region_short}"
    athena_workgroup                  = "${local.namespace}-${local.platform}-athena-workgroup-${local.environment_slug}-${local.region_short}"
    api_gateway                       = "${local.namespace}-${local.platform}-api-${local.environment_slug}-${local.region_short}"
    lambda_role                       = "${local.namespace}-${local.platform}-lambda-role-${local.environment_slug}-${local.region_short}"
    lambda_data_policy                = "${local.namespace}-${local.platform}-lambda-data-policy-${local.environment_slug}-${local.region_short}"
    monthly_ingest_state_machine      = "${local.namespace}-${local.platform}-monthly-ingest-workflow-${local.environment_slug}-${local.region_short}"
    monthly_ingest_state_machine_role = "${local.namespace}-${local.platform}-monthly-ingest-role-${local.environment_slug}-${local.region_short}"
    monthly_ingest_schedule_rule      = "${local.namespace}-${local.platform}-monthly-ingest-schedule-${local.environment_slug}-${local.region_short}"
    monthly_ingest_schedule_role      = "${local.namespace}-${local.platform}-monthly-ingest-schedule-role-${local.environment_slug}-${local.region_short}"
    monthly_ingest_staging_lambda     = "${local.namespace}-${local.platform}-monthly-ingest-staging-${local.environment_slug}-${local.region_short}"
    monthly_ingest_worker_repository  = "${local.namespace}-${local.platform}-monthly-ingest-worker-${local.environment_slug}-${local.region_short}"
    ingest_lambda                     = "${local.namespace}-${local.platform}-dataset-ingest-${local.environment_slug}-${local.region_short}"
    query_lambda                      = "${local.namespace}-${local.platform}-query-api-${local.environment_slug}-${local.region_short}"
    refresh_lambda                    = "${local.namespace}-${local.platform}-profile-refresh-${local.environment_slug}-${local.region_short}"
    form990_ingest_lambda             = "${local.namespace}-${local.platform}-form990-ingest-${local.environment_slug}-${local.region_short}"
    form990_orchestrator_lambda       = "${local.namespace}-${local.platform}-form990-orchestrator-${local.environment_slug}-${local.region_short}"
    form990_worker_lambda             = "${local.namespace}-${local.platform}-form990-worker-${local.environment_slug}-${local.region_short}"
    form990_work_dlq                  = "${local.namespace}-${local.platform}-form990-work-dlq-${local.environment_slug}-${local.region_short}"
    form990_work_queue                = "${local.namespace}-${local.platform}-form990-work-queue-${local.environment_slug}-${local.region_short}"
    daily_ingest_rule                 = "${local.namespace}-${local.platform}-daily-ingest-${local.environment_slug}-${local.region_short}"
    refresh_schedule_rule             = "${local.namespace}-${local.platform}-refresh-schedule-${local.environment_slug}-${local.region_short}"
    form990_schedule_rule             = "${local.namespace}-${local.platform}-form990-schedule-${local.environment_slug}-${local.region_short}"
  }

  legacy_resource_names = {
    source_data_bucket                = "${local.legacy_name_prefix}-irs-source-data-bucket"
    athena_results_bucket             = "${local.legacy_name_prefix}-athena-results"
    ecs_cluster                       = "${local.legacy_name_prefix}-platform-processing"
    profile_table                     = "${local.legacy_name_prefix}-profiles"
    identity_table                    = "identity"
    organization_settings_table       = "${local.legacy_name_prefix}-organization-settings"
    control_plane_table               = "${local.legacy_name_prefix}-control-plane"
    athena_workgroup                  = local.environment_slug == "prod" ? var.athena_workgroup_name : "${var.athena_workgroup_name}-${local.environment_slug}"
    api_gateway                       = "${local.legacy_name_prefix}-api"
    lambda_role                       = "${local.legacy_name_prefix}-lambda-role"
    lambda_data_policy                = "${local.legacy_name_prefix}-lambda-data-policy"
    monthly_ingest_state_machine      = "${local.legacy_name_prefix}-monthly-ingest-workflow"
    monthly_ingest_state_machine_role = "${local.legacy_name_prefix}-monthly-ingest-role"
    monthly_ingest_schedule_rule      = "${local.legacy_name_prefix}-monthly-ingest-schedule"
    monthly_ingest_schedule_role      = "${local.legacy_name_prefix}-monthly-ingest-schedule-role"
    monthly_ingest_staging_lambda     = "${local.legacy_name_prefix}-monthly-ingest-staging"
    monthly_ingest_worker_repository  = "${local.legacy_name_prefix}-monthly-ingest-worker"
    ingest_lambda                     = "${local.legacy_name_prefix}-dataset-ingest"
    query_lambda                      = "${local.legacy_name_prefix}-query-api"
    refresh_lambda                    = "${local.legacy_name_prefix}-profile-refresh"
    form990_ingest_lambda             = "${local.legacy_name_prefix}-form990-ingest"
    form990_orchestrator_lambda       = "${local.legacy_name_prefix}-form990-orchestrator"
    form990_worker_lambda             = "${local.legacy_name_prefix}-form990-worker"
    form990_work_dlq                  = "${local.legacy_name_prefix}-form990-work-dlq"
    form990_work_queue                = "${local.legacy_name_prefix}-form990-work-queue"
    daily_ingest_rule                 = "${local.legacy_name_prefix}-daily-ingest"
    refresh_schedule_rule             = "${local.legacy_name_prefix}-refresh-schedule"
    form990_schedule_rule             = "${local.legacy_name_prefix}-form990-schedule"
  }

  resource_names = {
    for key, legacy_name in local.legacy_resource_names :
    key => lookup(
      var.resource_name_overrides,
      key,
      var.resource_name_strategy == "standardized" ? local.standardized_resource_names[key] : legacy_name
    )
  }

  lambda_function_names = {
    regulatory_data_ingestion      = local.resource_names.ingest_lambda
    organization_verification_api  = local.resource_names.query_lambda
    platform_refresh               = local.resource_names.refresh_lambda
    monthly_private_ingest_staging = local.resource_names.monthly_ingest_staging_lambda
    regulatory_filing_ingestion    = local.resource_names.form990_ingest_lambda
    regulatory_filing_orchestrator = local.resource_names.form990_orchestrator_lambda
    regulatory_filing_worker       = local.resource_names.form990_worker_lambda
  }

  queue_names = {
    regulatory_filing_work_dead_letter = local.resource_names.form990_work_dlq
    regulatory_filing_work             = local.resource_names.form990_work_queue
  }

  scheduled_workflow_names = {
    regulatory_data_ingestion = local.resource_names.daily_ingest_rule
    platform_refresh          = local.resource_names.refresh_schedule_rule
    monthly_filing_ingestion  = local.resource_names.form990_schedule_rule
  }

  source_data_bucket_name                = local.resource_names.source_data_bucket
  athena_results_bucket_name             = local.resource_names.athena_results_bucket
  ecs_cluster_name                       = local.resource_names.ecs_cluster
  profile_table_name                     = local.resource_names.profile_table
  identity_table_name                    = local.resource_names.identity_table
  organization_settings_table_name       = local.resource_names.organization_settings_table
  control_plane_table_name               = local.resource_names.control_plane_table
  glue_database_name                     = "${local.data_catalog_prefix}_irs_db"
  athena_workgroup_resource_name         = local.resource_names.athena_workgroup
  api_gateway_name                       = local.resource_names.api_gateway
  lambda_role_name                       = local.resource_names.lambda_role
  lambda_data_policy_name                = local.resource_names.lambda_data_policy
  monthly_ingest_state_machine_name      = local.resource_names.monthly_ingest_state_machine
  monthly_ingest_state_machine_role_name = local.resource_names.monthly_ingest_state_machine_role
  monthly_ingest_schedule_rule_name      = local.resource_names.monthly_ingest_schedule_rule
  monthly_ingest_schedule_role_name      = local.resource_names.monthly_ingest_schedule_role
  monthly_ingest_staging_lambda_name     = local.lambda_function_names.monthly_private_ingest_staging
  monthly_ingest_worker_repository_name  = local.resource_names.monthly_ingest_worker_repository
  ingest_lambda_name                     = local.lambda_function_names.regulatory_data_ingestion
  query_lambda_name                      = local.lambda_function_names.organization_verification_api
  refresh_lambda_name                    = local.lambda_function_names.platform_refresh
  form990_ingest_lambda_name             = local.lambda_function_names.regulatory_filing_ingestion
  form990_orchestrator_lambda_name       = local.lambda_function_names.regulatory_filing_orchestrator
  form990_worker_lambda_name             = local.lambda_function_names.regulatory_filing_worker
  form990_work_dlq_name                  = local.queue_names.regulatory_filing_work_dead_letter
  form990_work_queue_name                = local.queue_names.regulatory_filing_work
  daily_ingest_rule_name                 = local.scheduled_workflow_names.regulatory_data_ingestion
  refresh_schedule_rule_name             = local.scheduled_workflow_names.platform_refresh
  form990_schedule_rule_name             = local.scheduled_workflow_names.monthly_filing_ingestion

  # GROUP is a SQL reserved word in Athena, so use group_name in the table schema.
  # This still maps to the 8th CSV column because OpenCSVSerde reads by position.
  eo_bmf_columns = [
    { name = "ein", type = "string" },
    { name = "name", type = "string" },
    { name = "ico", type = "string" },
    { name = "street", type = "string" },
    { name = "city", type = "string" },
    { name = "state", type = "string" },
    { name = "zip", type = "string" },
    { name = "group_name", type = "string" },
    { name = "subsection", type = "string" },
    { name = "affiliation", type = "string" },
    { name = "classification", type = "string" },
    { name = "ruling", type = "string" },
    { name = "deductibility", type = "string" },
    { name = "foundation", type = "string" },
    { name = "activity", type = "string" },
    { name = "organization", type = "string" },
    { name = "status", type = "string" },
    { name = "tax_period", type = "string" },
    { name = "asset_cd", type = "string" },
    { name = "income_cd", type = "string" },
    { name = "filing_req_cd", type = "string" },
    { name = "pf_filing_req_cd", type = "string" },
    { name = "acct_pd", type = "string" },
    { name = "asset_amt", type = "string" },
    { name = "income_amt", type = "string" },
    { name = "revenue_amt", type = "string" },
    { name = "ntee_cd", type = "string" },
    { name = "sort_name", type = "string" }
  ]

  form990_metadata_columns = [
    { name = "ein", type = "string" },
    { name = "tax_year", type = "string" },
    { name = "tax_period_begin", type = "string" },
    { name = "tax_period_end", type = "string" },
    { name = "filing_date", type = "string" },
    { name = "amended_return", type = "boolean" },
    { name = "return_type", type = "string" },
    { name = "irs_object_id", type = "string" },
    { name = "xml_source_reference", type = "string" },
    { name = "raw_s3_key", type = "string" },
    { name = "parse_status", type = "string" },
    { name = "parse_error", type = "string" },
    { name = "total_revenue", type = "double" },
    { name = "mission_description_present", type = "boolean" },
    { name = "program_accomplishments_present", type = "boolean" },
    { name = "leadership_disclosed", type = "boolean" }
  ]

  form990_metrics_columns = [
    { name = "ein", type = "string" },
    { name = "tax_year", type = "string" },
    { name = "programExpenseRatio", type = "double" },
    { name = "adminExpenseRatio", type = "double" },
    { name = "fundraisingRatio", type = "double" },
    { name = "liabilitiesToAssetsRatio", type = "double" },
    { name = "operatingMargin", type = "double" },
    { name = "fundraisingEfficiency", type = "double" },
    { name = "workingCapital", type = "double" },
    { name = "monthsOfRunway", type = "double" }
  ]

  form990_governance_columns = [
    { name = "ein", type = "string" },
    { name = "tax_year", type = "string" },
    { name = "independent_board_majority", type = "boolean" },
    { name = "conflict_of_interest_policy", type = "boolean" },
    { name = "whistleblower_policy", type = "boolean" },
    { name = "records_retention_policy", type = "boolean" },
    { name = "contemporaneous_board_minutes", type = "boolean" },
    { name = "material_diversion_reported", type = "boolean" },
    { name = "compensation_review_process", type = "boolean" },
    { name = "public_disclosure_available", type = "boolean" },
    { name = "audited_financials_indicator", type = "boolean" }
  ]

  form990_quality_columns = [
    { name = "ein", type = "string" },
    { name = "tax_year", type = "string" },
    { name = "missingRequiredFieldsCount", type = "int" },
    { name = "internalConsistencyIssuesCount", type = "int" },
    { name = "staleFilingDays", type = "int" },
    { name = "narrativeMissing", type = "boolean" },
    { name = "anomalyFlags", type = "array<string>" },
    { name = "scoreConfidence", type = "string" }
  ]

  platform_common_tags = merge({
    PlatformNamespace = "verification_platform"
    PlatformDomain    = "organization_verification"
    PlatformLayer     = "infrastructure"
    NamingStrategy    = var.resource_name_strategy
    }, {
    Project     = var.base_name
    Environment = var.environment
    ManagedBy   = "terraform"
  })
  common_tags = local.platform_common_tags
}

resource "aws_s3_bucket" "athena_results" {
  bucket = local.athena_results_bucket_name
  tags   = local.platform_common_tags
}

resource "aws_s3_bucket_public_access_block" "athena_results" {
  bucket = aws_s3_bucket.athena_results.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_athena_workgroup" "eo_bmf" {
  name = local.athena_workgroup_resource_name

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true

    result_configuration {
      output_location = "s3://${aws_s3_bucket.athena_results.bucket}/results/"
    }
  }

  force_destroy = var.environment != "prod"
  tags          = local.platform_common_tags
}

resource "aws_glue_catalog_database" "eo_bmf" {
  name = local.glue_database_name
}

resource "aws_glue_catalog_table" "eo_bmf" {
  name          = "eo_bmf"
  database_name = aws_glue_catalog_database.eo_bmf.name
  table_type    = "EXTERNAL_TABLE"
  parameters = {
    EXTERNAL                 = "TRUE"
    classification           = "csv"
    "skip.header.line.count" = "1"
  }

  storage_descriptor {
    location      = "s3://${local.source_data_bucket_name}/${local.source_data_prefix_normalized}"
    input_format  = "org.apache.hadoop.mapred.TextInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.serde2.OpenCSVSerde"
      parameters = {
        separatorChar = ","
        quoteChar     = "\""
        escapeChar    = "\\"
      }
    }

    dynamic "columns" {
      for_each = local.eo_bmf_columns
      content {
        name = columns.value.name
        type = columns.value.type
      }
    }
  }
}

resource "aws_glue_catalog_table" "form990_metadata" {
  name          = "form990_metadata"
  database_name = aws_glue_catalog_database.eo_bmf.name
  table_type    = "EXTERNAL_TABLE"
  parameters = {
    EXTERNAL       = "TRUE"
    classification = "json"
  }

  storage_descriptor {
    location      = "s3://${local.source_data_bucket_name}/${local.form990_metadata_prefix_normalized}"
    input_format  = "org.apache.hadoop.mapred.TextInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.IgnoreKeyTextOutputFormat"

    ser_de_info {
      serialization_library = "org.openx.data.jsonserde.JsonSerDe"
    }

    dynamic "columns" {
      for_each = local.form990_metadata_columns
      content {
        name = columns.value.name
        type = columns.value.type
      }
    }
  }
}

resource "aws_glue_catalog_table" "form990_metrics" {
  name          = "form990_metrics"
  database_name = aws_glue_catalog_database.eo_bmf.name
  table_type    = "EXTERNAL_TABLE"
  parameters = {
    EXTERNAL       = "TRUE"
    classification = "json"
  }

  storage_descriptor {
    location      = "s3://${local.source_data_bucket_name}/${local.form990_metrics_prefix_normalized}"
    input_format  = "org.apache.hadoop.mapred.TextInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.IgnoreKeyTextOutputFormat"

    ser_de_info {
      serialization_library = "org.openx.data.jsonserde.JsonSerDe"
    }

    dynamic "columns" {
      for_each = local.form990_metrics_columns
      content {
        name = columns.value.name
        type = columns.value.type
      }
    }
  }
}

resource "aws_glue_catalog_table" "form990_governance" {
  name          = "form990_governance"
  database_name = aws_glue_catalog_database.eo_bmf.name
  table_type    = "EXTERNAL_TABLE"
  parameters = {
    EXTERNAL       = "TRUE"
    classification = "json"
  }

  storage_descriptor {
    location      = "s3://${local.source_data_bucket_name}/${local.form990_governance_prefix_normalized}"
    input_format  = "org.apache.hadoop.mapred.TextInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.IgnoreKeyTextOutputFormat"

    ser_de_info {
      serialization_library = "org.openx.data.jsonserde.JsonSerDe"
    }

    dynamic "columns" {
      for_each = local.form990_governance_columns
      content {
        name = columns.value.name
        type = columns.value.type
      }
    }
  }
}

resource "aws_glue_catalog_table" "form990_quality" {
  name          = "form990_quality"
  database_name = aws_glue_catalog_database.eo_bmf.name
  table_type    = "EXTERNAL_TABLE"
  parameters = {
    EXTERNAL       = "TRUE"
    classification = "json"
  }

  storage_descriptor {
    location      = "s3://${local.source_data_bucket_name}/${local.form990_quality_prefix_normalized}"
    input_format  = "org.apache.hadoop.mapred.TextInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.IgnoreKeyTextOutputFormat"

    ser_de_info {
      serialization_library = "org.openx.data.jsonserde.JsonSerDe"
    }

    dynamic "columns" {
      for_each = local.form990_quality_columns
      content {
        name = columns.value.name
        type = columns.value.type
      }
    }
  }
}

resource "aws_dynamodb_table" "profiles" {
  name         = local.profile_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  range_key    = "sk"

  attribute {
    name = "pk"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }

  tags = local.platform_common_tags
}

resource "aws_dynamodb_table" "identity" {
  name         = local.identity_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  range_key    = "sk"

  # DynamoDB GSI creation backfills asynchronously and can exceed Terraform's
  # default update wait on existing tables.
  timeouts {
    update = "2h"
  }

  attribute {
    name = "pk"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }

  attribute {
    name = "gsi1pk"
    type = "S"
  }

  attribute {
    name = "gsi1sk"
    type = "S"
  }

  attribute {
    name = "gsi2pk"
    type = "S"
  }

  attribute {
    name = "gsi2sk"
    type = "S"
  }

  attribute {
    name = "gsi3pk"
    type = "S"
  }

  attribute {
    name = "gsi3sk"
    type = "S"
  }

  attribute {
    name = "gsi4pk"
    type = "S"
  }

  attribute {
    name = "gsi4sk"
    type = "S"
  }

  attribute {
    name = "gsi5pk"
    type = "S"
  }

  attribute {
    name = "gsi5sk"
    type = "S"
  }

  global_secondary_index {
    name            = "email_lookup"
    hash_key        = "gsi1pk"
    range_key       = "gsi1sk"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "user_memberships"
    hash_key        = "gsi2pk"
    range_key       = "gsi2sk"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "invitation_token_lookup"
    hash_key        = "gsi3pk"
    range_key       = "gsi3sk"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "organization_slug_lookup"
    hash_key        = "gsi4pk"
    range_key       = "gsi4sk"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "api_key_lookup"
    hash_key        = "gsi5pk"
    range_key       = "gsi5sk"
    projection_type = "ALL"
  }

  tags = local.platform_common_tags
}

resource "aws_dynamodb_table" "organization_settings" {
  name         = local.organization_settings_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  range_key    = "sk"

  attribute {
    name = "pk"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }

  attribute {
    name = "account_id"
    type = "S"
  }

  global_secondary_index {
    name            = "account_lookup"
    hash_key        = "account_id"
    projection_type = "ALL"
  }

  tags = local.platform_common_tags
}

resource "aws_dynamodb_table" "control_plane" {
  name         = local.control_plane_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  range_key    = "sk"

  attribute {
    name = "pk"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }

  attribute {
    name = "gsi1pk"
    type = "S"
  }

  attribute {
    name = "gsi1sk"
    type = "S"
  }

  attribute {
    name = "gsi2pk"
    type = "S"
  }

  attribute {
    name = "gsi2sk"
    type = "S"
  }

  global_secondary_index {
    name            = "credential_lookup"
    hash_key        = "gsi1pk"
    range_key       = "gsi1sk"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "entity_listing"
    hash_key        = "gsi2pk"
    range_key       = "gsi2sk"
    projection_type = "ALL"
  }

  tags = local.platform_common_tags
}
