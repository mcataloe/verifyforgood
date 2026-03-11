locals {
  domain_name                          = var.root_domain_name != "" ? var.root_domain_name : "${var.base_name}.com"
  source_data_prefix_normalized        = "${trim(var.source_data_prefix, "/")}/"
  form990_raw_prefix_normalized        = "${trim(var.form990_raw_prefix, "/")}/"
  form990_metadata_prefix_normalized   = "${trim(var.form990_metadata_prefix, "/")}/"
  form990_manifest_prefix_normalized   = "${trim(var.form990_manifest_prefix, "/")}/"
  form990_metrics_prefix_normalized    = "${trim(var.form990_metrics_prefix, "/")}/"
  form990_governance_prefix_normalized = "${trim(var.form990_governance_prefix, "/")}/"
  form990_quality_prefix_normalized    = "${trim(var.form990_quality_prefix, "/")}/"
  source_data_bucket_name              = "${var.base_name}-irs-source-data-bucket"
  athena_results_bucket_name           = "${var.base_name}-athena-results"
  glue_database_name                   = "${var.base_name}_irs_db"

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
    { name = "parse_error", type = "string" }
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

  common_tags = {
    Project     = var.base_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_s3_bucket" "athena_results" {
  bucket = var.environment == "prod" ? local.athena_results_bucket_name : "${local.athena_results_bucket_name}-${var.environment}"
  tags   = local.common_tags
}

resource "aws_s3_bucket_public_access_block" "athena_results" {
  bucket = aws_s3_bucket.athena_results.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_athena_workgroup" "eo_bmf" {
  name = "${var.athena_workgroup_name}-${var.environment}"

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true

    result_configuration {
      output_location = "s3://${aws_s3_bucket.athena_results.bucket}/results/"
    }
  }

  force_destroy = var.environment != "prod"
  tags          = local.common_tags
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
