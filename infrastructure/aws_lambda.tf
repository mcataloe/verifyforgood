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
  count       = local.use_ingest_build_dir ? 0 : 1
  type        = "zip"
  source_file = "${path.module}/lambda_ingest.py"
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
    "charity_status/ingest/**",
    "charity_status/future/**",
    "ingest.zip",
    "query.zip",
    "lambda_ingest.py",
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
      DATABASE  = aws_glue_catalog_database.eo_bmf.name
      TABLE     = aws_glue_catalog_table.eo_bmf.name
      WORKGROUP = aws_athena_workgroup.eo_bmf.name
    }
  }
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
