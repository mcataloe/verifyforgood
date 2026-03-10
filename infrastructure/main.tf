provider "aws" {
  region = var.region
}

#############################################
# S3 BUCKET FOR IRS DATA
#############################################

resource "aws_s3_bucket" "irs_data" {
  bucket = "irs-nonprofit-datasets-${random_id.rand.hex}"
}

resource "random_id" "rand" {
  byte_length = 4
}

#############################################
# IAM ROLE FOR LAMBDAS
#############################################

resource "aws_iam_role" "lambda_role" {
  name = "irs_api_lambda_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "basic_lambda" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_data_access" {
  name = "irs_lambda_data_policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:*",
          "athena:*",
          "glue:*"
        ]
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })
}

#############################################
# LAMBDA - IRS DATA INGESTION
#############################################

data "archive_file" "ingest_zip" {
  type        = "zip"
  source_dir  = "${path.module}/build/ingest_package"
  output_path = "${path.module}/ingest.zip"
}

resource "aws_lambda_function" "ingest" {

  function_name = "irs_dataset_ingest"
  handler       = "lambda_ingest.handler"
  runtime       = "python3.11"
  role          = aws_iam_role.lambda_role.arn
  timeout       = 300

  filename         = data.archive_file.ingest_zip.output_path
  source_code_hash = data.archive_file.ingest_zip.output_base64sha256

  environment {
    variables = {
      BUCKET = aws_s3_bucket.irs_data.bucket
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

#############################################
# LAMBDA QUERY FUNCTION
#############################################

data "archive_file" "query_zip" {
  type        = "zip"
  source_file = "${path.module}/lambda_query.py"
  output_path = "${path.module}/query.zip"
}

resource "aws_lambda_function" "query" {

  function_name = "irs_query_api"
  handler       = "lambda_query.handler"
  runtime       = "python3.11"
  role          = aws_iam_role.lambda_role.arn
  timeout       = 30

  filename         = data.archive_file.query_zip.output_path
  source_code_hash = data.archive_file.query_zip.output_base64sha256
}

#############################################
# API GATEWAY
#############################################

resource "aws_api_gateway_rest_api" "irs_api" {
  name = "irs-nonprofit-api"
}

resource "aws_api_gateway_resource" "ein" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_rest_api.irs_api.root_resource_id
  path_part   = "nonprofit"
}

resource "aws_api_gateway_resource" "ein_id" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.ein.id
  path_part   = "{ein}"
}

resource "aws_api_gateway_method" "get_ein" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.ein_id.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "lambda_integration" {

  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  resource_id = aws_api_gateway_resource.ein_id.id
  http_method = aws_api_gateway_method.get_ein.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.query.invoke_arn
}

resource "aws_lambda_permission" "api_gw" {
  statement_id  = "AllowApiGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.query.function_name
  principal     = "apigateway.amazonaws.com"

  source_arn = "${aws_api_gateway_rest_api.irs_api.execution_arn}/*/*"
}

resource "aws_api_gateway_deployment" "deployment" {

  depends_on = [
    aws_api_gateway_integration.lambda_integration
  ]

  rest_api_id = aws_api_gateway_rest_api.irs_api.id
}

resource "aws_api_gateway_stage" "prod" {
  deployment_id = aws_api_gateway_deployment.deployment.id
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  stage_name    = "prod"
}

resource "aws_api_gateway_stage" "dev" {
  deployment_id = aws_api_gateway_deployment.deployment.id
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  stage_name    = "dev"
}


#############################################
# ACM CERTIFICATE
#############################################

resource "aws_acm_certificate" "cert" {
  domain_name       = var.domain_name
  validation_method = "DNS"
}

#############################################
# API CUSTOM DOMAIN
#############################################

resource "aws_api_gateway_domain_name" "api_domain" {
  domain_name = var.domain_name

  certificate_arn = aws_acm_certificate.cert.arn
}

resource "aws_api_gateway_base_path_mapping" "mapping" {

  api_id      = aws_api_gateway_rest_api.irs_api.id
  stage_name  = aws_api_gateway_stage.prod.stage_name
  domain_name = aws_api_gateway_domain_name.api_domain.domain_name
}

#############################################
# ROUTE53 RECORD
#############################################

resource "aws_route53_record" "api_record" {

  zone_id = var.hosted_zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = aws_api_gateway_domain_name.api_domain.cloudfront_domain_name
    zone_id                = aws_api_gateway_domain_name.api_domain.cloudfront_zone_id
    evaluate_target_health = false
  }
}
