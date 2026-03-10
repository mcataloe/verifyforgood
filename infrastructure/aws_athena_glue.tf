# README
# This Terraform config creates static Athena + Glue metadata infrastructure for
# querying IRS EO BMF CSV files already stored in S3.
#
# Data flow:
# 1) Source CSV files are already present in S3 under schema-specific prefixes.
# 2) Glue Data Catalog database + external tables map those prefixes with explicit schemas.
# 3) Athena workgroup uses Glue catalog tables and writes query results to a dedicated S3 bucket.
#
# Customize before deploy:
# - project_name, environment
# - source_data_bucket_name
# - athena_results_bucket_name
# - glue_database_name
# - per-table prefixes and column definitions (TODO markers below)
#
# Athena query example after deployment:
# SELECT ein, organization_name, city, state
# FROM "<glue_database_name>"."<project>_<env>_eo1"
# LIMIT 25;

locals {
  effective_environment = var.environment
  table_name_prefix     = lower(replace("${var.project_name}_${local.effective_environment}", "-", "_"))

  # Normalize prefixes to always produce s3://bucket/prefix/
  eo1_prefix_normalized   = "${trim(var.eo1_prefix, "/")}/"
  eo2_prefix_normalized   = "${trim(var.eo2_prefix, "/")}/"
  eo3_prefix_normalized   = "${trim(var.eo3_prefix, "/")}/"
  eo4_prefix_normalized   = "${trim(var.eo4_prefix, "/")}/"
  eo_pr_prefix_normalized = "${trim(var.eo_pr_prefix, "/")}/"
  eo_xx_prefix_normalized = "${trim(var.eo_xx_prefix, "/")}/"

  common_tags = {
    Project     = var.project_name
    Environment = local.effective_environment
    ManagedBy   = "terraform"
  }

  glue_table_common_parameters = {
    EXTERNAL                 = "TRUE"
    classification           = "csv"
    "skip.header.line.count" = "1"
  }

  csv_serde_parameters = {
    separatorChar = ","
    quoteChar     = "\""
    escapeChar    = "\\"
  }

  # IRS EO BMF CSV header:
  # EIN,NAME,ICO,STREET,CITY,STATE,ZIP,GROUP,SUBSECTION,AFFILIATION,CLASSIFICATION,RULING,DEDUCTIBILITY,FOUNDATION,ACTIVITY,ORGANIZATION,STATUS,TAX_PERIOD,ASSET_CD,INCOME_CD,FILING_REQ_CD,PF_FILING_REQ_CD,ACCT_PD,ASSET_AMT,INCOME_AMT,REVENUE_AMT,NTEE_CD,SORT_NAME
  eo_bmf_columns = [
    { name = "ein", type = "string" },
    { name = "name", type = "string" },
    { name = "ico", type = "string" },
    { name = "street", type = "string" },
    { name = "city", type = "string" },
    { name = "state", type = "string" },
    { name = "zip", type = "string" },
    { name = "group_number", type = "string" },
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
}

resource "aws_s3_bucket" "athena_results" {
  bucket = var.environment == "prod" ? var.athena_results_bucket_name : "${var.athena_results_bucket_name}-${var.environment}"
  tags   = local.common_tags
}

resource "aws_s3_bucket_public_access_block" "athena_results" {
  bucket = aws_s3_bucket.athena_results.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_athena_workgroup" "irs" {
  name = "${var.project_name}-${local.effective_environment}-athena"

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true

    result_configuration {
      output_location = "s3://${aws_s3_bucket.athena_results.bucket}/results/"
    }
  }

  force_destroy = false
  tags          = local.common_tags
}

resource "aws_glue_catalog_database" "irs" {
  name = var.environment == "prod" ? var.glue_database_name : "${var.glue_database_name}_${var.environment}"
}

resource "aws_glue_catalog_table" "eo1" {
  name          = "${local.table_name_prefix}_eo1"
  database_name = aws_glue_catalog_database.irs.name
  table_type    = "EXTERNAL_TABLE"
  parameters    = local.glue_table_common_parameters

  storage_descriptor {
    location      = "s3://${var.source_data_bucket_name}/${local.eo1_prefix_normalized}"
    input_format  = "org.apache.hadoop.mapred.TextInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.serde2.OpenCSVSerde"
      parameters            = local.csv_serde_parameters
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

resource "aws_glue_catalog_table" "eo2" {
  name          = "${local.table_name_prefix}_eo2"
  database_name = aws_glue_catalog_database.irs.name
  table_type    = "EXTERNAL_TABLE"
  parameters    = local.glue_table_common_parameters

  storage_descriptor {
    location      = "s3://${var.source_data_bucket_name}/${local.eo2_prefix_normalized}"
    input_format  = "org.apache.hadoop.mapred.TextInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.serde2.OpenCSVSerde"
      parameters            = local.csv_serde_parameters
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

resource "aws_glue_catalog_table" "eo3" {
  name          = "${local.table_name_prefix}_eo3"
  database_name = aws_glue_catalog_database.irs.name
  table_type    = "EXTERNAL_TABLE"
  parameters    = local.glue_table_common_parameters

  storage_descriptor {
    location      = "s3://${var.source_data_bucket_name}/${local.eo3_prefix_normalized}"
    input_format  = "org.apache.hadoop.mapred.TextInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.serde2.OpenCSVSerde"
      parameters            = local.csv_serde_parameters
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

resource "aws_glue_catalog_table" "eo4" {
  name          = "${local.table_name_prefix}_eo4"
  database_name = aws_glue_catalog_database.irs.name
  table_type    = "EXTERNAL_TABLE"
  parameters    = local.glue_table_common_parameters

  storage_descriptor {
    location      = "s3://${var.source_data_bucket_name}/${local.eo4_prefix_normalized}"
    input_format  = "org.apache.hadoop.mapred.TextInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.serde2.OpenCSVSerde"
      parameters            = local.csv_serde_parameters
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

resource "aws_glue_catalog_table" "eo_pr" {
  name          = "${local.table_name_prefix}_eo_pr"
  database_name = aws_glue_catalog_database.irs.name
  table_type    = "EXTERNAL_TABLE"
  parameters    = local.glue_table_common_parameters

  storage_descriptor {
    location      = "s3://${var.source_data_bucket_name}/${local.eo_pr_prefix_normalized}"
    input_format  = "org.apache.hadoop.mapred.TextInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.serde2.OpenCSVSerde"
      parameters            = local.csv_serde_parameters
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

resource "aws_glue_catalog_table" "eo_xx" {
  name          = "${local.table_name_prefix}_eo_xx"
  database_name = aws_glue_catalog_database.irs.name
  table_type    = "EXTERNAL_TABLE"
  parameters    = local.glue_table_common_parameters

  storage_descriptor {
    location      = "s3://${var.source_data_bucket_name}/${local.eo_xx_prefix_normalized}"
    input_format  = "org.apache.hadoop.mapred.TextInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.serde2.OpenCSVSerde"
      parameters            = local.csv_serde_parameters
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
