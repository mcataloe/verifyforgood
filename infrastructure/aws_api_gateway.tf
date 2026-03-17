
#############################################
# API GATEWAY
#############################################

resource "aws_api_gateway_rest_api" "irs_api" {
  name = "${local.domain_name}${var.environment == "prod" ? "" : "-${var.environment}"}"
}

resource "aws_api_gateway_resource" "api_v1" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_rest_api.irs_api.root_resource_id
  path_part   = "v1"
}

resource "aws_api_gateway_resource" "ein" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.api_v1.id
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
  parent_id   = aws_api_gateway_resource.api_v1.id
  path_part   = "verify"
}

resource "aws_api_gateway_resource" "oauth" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.api_v1.id
  path_part   = "oauth"
}

resource "aws_api_gateway_resource" "oauth_token" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.oauth.id
  path_part   = "token"
}

resource "aws_api_gateway_resource" "nonprofits" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.api_v1.id
  path_part   = "nonprofits"
}

resource "aws_api_gateway_resource" "nonprofits_search" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.nonprofits.id
  path_part   = "search"
}

resource "aws_api_gateway_resource" "nonprofits_ein" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.nonprofits.id
  path_part   = "{ein}"
}

resource "aws_api_gateway_resource" "nonprofits_sources" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.nonprofits_ein.id
  path_part   = "sources"
}

resource "aws_api_gateway_resource" "nonprofits_source_name" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.nonprofits_sources.id
  path_part   = "{source_name}"
}

resource "aws_api_gateway_resource" "nonprofits_compliance" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.nonprofits_ein.id
  path_part   = "compliance"
}

resource "aws_api_gateway_resource" "nonprofits_federal_awards" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.nonprofits_ein.id
  path_part   = "federal-awards"
}

resource "aws_api_gateway_resource" "verify_batch" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.verify.id
  path_part   = "batch"
}

resource "aws_api_gateway_resource" "organizations" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.api_v1.id
  path_part   = "organizations"
}

resource "aws_api_gateway_resource" "organizations_integrations" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.organizations.id
  path_part   = "integrations"
}

resource "aws_api_gateway_resource" "ops" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.api_v1.id
  path_part   = "ops"
}

resource "aws_api_gateway_resource" "ops_ingest" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.ops.id
  path_part   = "ingest"
}

resource "aws_api_gateway_resource" "ops_ingest_runs" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.ops_ingest.id
  path_part   = "runs"
}

resource "aws_api_gateway_resource" "ops_ingest_run_id" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.ops_ingest_runs.id
  path_part   = "{ingest_run_id}"
}

resource "aws_api_gateway_resource" "ops_ingest_run_filings" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.ops_ingest_run_id.id
  path_part   = "filings"
}

resource "aws_api_gateway_resource" "ops_refresh" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.ops.id
  path_part   = "refresh"
}

resource "aws_api_gateway_resource" "ops_refresh_runs" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.ops_refresh.id
  path_part   = "runs"
}

resource "aws_api_gateway_resource" "ops_refresh_run_id" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.ops_refresh_runs.id
  path_part   = "{refresh_run_id}"
}

resource "aws_api_gateway_resource" "ops_refresh_run_eins" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.ops_refresh_run_id.id
  path_part   = "eins"
}

resource "aws_api_gateway_resource" "ops_nonprofits" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.ops.id
  path_part   = "nonprofits"
}

resource "aws_api_gateway_resource" "ops_nonprofit_ein" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.ops_nonprofits.id
  path_part   = "{ein}"
}

resource "aws_api_gateway_resource" "ops_nonprofit_pipeline_status" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.ops_nonprofit_ein.id
  path_part   = "pipeline-status"
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

resource "aws_api_gateway_method" "post_oauth_token" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.oauth_token.id
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

resource "aws_api_gateway_integration" "lambda_oauth_token_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.oauth_token.id
  http_method             = aws_api_gateway_method.post_oauth_token.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.query.invoke_arn
}

resource "aws_api_gateway_method" "get_nonprofits_search" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.nonprofits_search.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "lambda_nonprofits_search_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.nonprofits_search.id
  http_method             = aws_api_gateway_method.get_nonprofits_search.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.query.invoke_arn
}

resource "aws_api_gateway_method" "get_nonprofits_sources" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.nonprofits_sources.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "lambda_nonprofits_sources_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.nonprofits_sources.id
  http_method             = aws_api_gateway_method.get_nonprofits_sources.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.query.invoke_arn
}

resource "aws_api_gateway_method" "get_nonprofits_source_name" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.nonprofits_source_name.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "lambda_nonprofits_source_name_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.nonprofits_source_name.id
  http_method             = aws_api_gateway_method.get_nonprofits_source_name.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.query.invoke_arn
}

resource "aws_api_gateway_method" "get_nonprofits_compliance" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.nonprofits_compliance.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "lambda_nonprofits_compliance_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.nonprofits_compliance.id
  http_method             = aws_api_gateway_method.get_nonprofits_compliance.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.query.invoke_arn
}

resource "aws_api_gateway_method" "get_nonprofits_federal_awards" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.nonprofits_federal_awards.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "lambda_nonprofits_federal_awards_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.nonprofits_federal_awards.id
  http_method             = aws_api_gateway_method.get_nonprofits_federal_awards.http_method
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

resource "aws_api_gateway_method" "get_organizations_integrations" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.organizations_integrations.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "put_organizations_integrations" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.organizations_integrations.id
  http_method   = "PUT"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "get_ops_ingest_runs" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.ops_ingest_runs.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "get_ops_ingest_run_id" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.ops_ingest_run_id.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "get_ops_ingest_run_filings" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.ops_ingest_run_filings.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "get_ops_refresh_runs" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.ops_refresh_runs.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "get_ops_refresh_run_id" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.ops_refresh_run_id.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "get_ops_refresh_run_eins" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.ops_refresh_run_eins.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "get_ops_nonprofit_pipeline_status" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.ops_nonprofit_pipeline_status.id
  http_method   = "GET"
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

resource "aws_api_gateway_integration" "lambda_get_organizations_integrations_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.organizations_integrations.id
  http_method             = aws_api_gateway_method.get_organizations_integrations.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.query.invoke_arn
}

resource "aws_api_gateway_integration" "lambda_put_organizations_integrations_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.organizations_integrations.id
  http_method             = aws_api_gateway_method.put_organizations_integrations.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.query.invoke_arn
}

resource "aws_api_gateway_integration" "lambda_ops_ingest_runs_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.ops_ingest_runs.id
  http_method             = aws_api_gateway_method.get_ops_ingest_runs.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.query.invoke_arn
}

resource "aws_api_gateway_integration" "lambda_ops_ingest_run_id_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.ops_ingest_run_id.id
  http_method             = aws_api_gateway_method.get_ops_ingest_run_id.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.query.invoke_arn
}

resource "aws_api_gateway_integration" "lambda_ops_ingest_run_filings_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.ops_ingest_run_filings.id
  http_method             = aws_api_gateway_method.get_ops_ingest_run_filings.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.query.invoke_arn
}

resource "aws_api_gateway_integration" "lambda_ops_refresh_runs_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.ops_refresh_runs.id
  http_method             = aws_api_gateway_method.get_ops_refresh_runs.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.query.invoke_arn
}

resource "aws_api_gateway_integration" "lambda_ops_refresh_run_id_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.ops_refresh_run_id.id
  http_method             = aws_api_gateway_method.get_ops_refresh_run_id.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.query.invoke_arn
}

resource "aws_api_gateway_integration" "lambda_ops_refresh_run_eins_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.ops_refresh_run_eins.id
  http_method             = aws_api_gateway_method.get_ops_refresh_run_eins.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.query.invoke_arn
}

resource "aws_api_gateway_integration" "lambda_ops_nonprofit_pipeline_status_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.ops_nonprofit_pipeline_status.id
  http_method             = aws_api_gateway_method.get_ops_nonprofit_pipeline_status.http_method
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
    aws_api_gateway_integration.lambda_oauth_token_integration,
    aws_api_gateway_integration.lambda_verify_batch_integration,
    aws_api_gateway_integration.lambda_get_organizations_integrations_integration,
    aws_api_gateway_integration.lambda_put_organizations_integrations_integration,
    aws_api_gateway_integration.lambda_nonprofits_search_integration,
    aws_api_gateway_integration.lambda_nonprofits_sources_integration,
    aws_api_gateway_integration.lambda_nonprofits_source_name_integration,
    aws_api_gateway_integration.lambda_nonprofits_compliance_integration,
    aws_api_gateway_integration.lambda_nonprofits_federal_awards_integration,
    aws_api_gateway_integration.lambda_ops_ingest_runs_integration,
    aws_api_gateway_integration.lambda_ops_ingest_run_id_integration,
    aws_api_gateway_integration.lambda_ops_ingest_run_filings_integration,
    aws_api_gateway_integration.lambda_ops_refresh_runs_integration,
    aws_api_gateway_integration.lambda_ops_refresh_run_id_integration,
    aws_api_gateway_integration.lambda_ops_refresh_run_eins_integration,
    aws_api_gateway_integration.lambda_ops_nonprofit_pipeline_status_integration
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
