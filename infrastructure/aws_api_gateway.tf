
#############################################
# API GATEWAY
#############################################

resource "aws_api_gateway_rest_api" "irs_api" {
  name = "${local.domain_name}${var.environment == "prod" ? "" : "-${var.environment}"}"
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

resource "aws_api_gateway_resource" "ein_filings" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.ein_id.id
  path_part   = "filings"
}

resource "aws_api_gateway_resource" "verify" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_rest_api.irs_api.root_resource_id
  path_part   = "verify"
}

resource "aws_api_gateway_resource" "verify_batch" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.verify.id
  path_part   = "batch"
}

resource "aws_api_gateway_method" "get_ein" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.ein_id.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "get_ein_filings" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.ein_filings.id
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

resource "aws_api_gateway_integration" "lambda_filings_integration" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  resource_id = aws_api_gateway_resource.ein_filings.id
  http_method = aws_api_gateway_method.get_ein_filings.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.query.invoke_arn
}

resource "aws_api_gateway_method" "post_verify" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.verify.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "lambda_verify_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.verify.id
  http_method             = aws_api_gateway_method.post_verify.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.query.invoke_arn
}

resource "aws_api_gateway_method" "post_verify_batch" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.verify_batch.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "lambda_verify_batch_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.verify_batch.id
  http_method             = aws_api_gateway_method.post_verify_batch.http_method
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
    aws_api_gateway_integration.lambda_integration,
    aws_api_gateway_integration.lambda_filings_integration,
    aws_api_gateway_integration.lambda_verify_integration,
    aws_api_gateway_integration.lambda_verify_batch_integration
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
