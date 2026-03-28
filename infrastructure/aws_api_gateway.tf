
#############################################
# API GATEWAY
#############################################

resource "aws_api_gateway_rest_api" "irs_api" {
  name = local.api_gateway_name
}

resource "aws_api_gateway_resource" "api_v1" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_rest_api.irs_api.root_resource_id
  path_part   = "v1"
}

resource "aws_api_gateway_resource" "auth" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.api_v1.id
  path_part   = "auth"
}

resource "aws_api_gateway_resource" "auth_register" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.auth.id
  path_part   = "register"
}

resource "aws_api_gateway_resource" "auth_login" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.auth.id
  path_part   = "login"
}

resource "aws_api_gateway_resource" "auth_me" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.auth.id
  path_part   = "me"
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

resource "aws_api_gateway_resource" "webhooks" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.api_v1.id
  path_part   = "webhooks"
}

resource "aws_api_gateway_resource" "webhooks_stripe" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.webhooks.id
  path_part   = "stripe"
}

resource "aws_api_gateway_resource" "admin" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.api_v1.id
  path_part   = "admin"
}

resource "aws_api_gateway_resource" "admin_accounts" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.admin.id
  path_part   = "accounts"
}

resource "aws_api_gateway_resource" "admin_account_id" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.admin_accounts.id
  path_part   = "{accountId}"
}

resource "aws_api_gateway_resource" "admin_account_suspend" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.admin_account_id.id
  path_part   = "suspend"
}

resource "aws_api_gateway_resource" "admin_account_activate" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.admin_account_id.id
  path_part   = "activate"
}

resource "aws_api_gateway_resource" "admin_account_subscription" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.admin_account_id.id
  path_part   = "subscription"
}

resource "aws_api_gateway_resource" "admin_account_api_keys" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.admin_account_id.id
  path_part   = "api-keys"
}

resource "aws_api_gateway_resource" "admin_account_api_key_id" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.admin_account_api_keys.id
  path_part   = "{keyId}"
}

resource "aws_api_gateway_resource" "admin_account_api_key_rotate" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.admin_account_api_key_id.id
  path_part   = "rotate"
}

resource "aws_api_gateway_resource" "admin_account_oauth_clients" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.admin_account_id.id
  path_part   = "oauth-clients"
}

resource "aws_api_gateway_resource" "admin_account_oauth_client_id" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.admin_account_oauth_clients.id
  path_part   = "{clientId}"
}

resource "aws_api_gateway_resource" "nonprofits" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.api_v1.id
  path_part   = "nonprofits"
}

resource "aws_api_gateway_resource" "nonprofits_verify" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.nonprofits.id
  path_part   = "verify"
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

resource "aws_api_gateway_resource" "plans" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.api_v1.id
  path_part   = "plans"
}

resource "aws_api_gateway_resource" "verify_batch" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.verify.id
  path_part   = "batch"
}

resource "aws_api_gateway_resource" "organizations" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.api_v1.id
  path_part   = "organization"
}

resource "aws_api_gateway_resource" "portal_organizations" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.api_v1.id
  path_part   = "organizations"
}

resource "aws_api_gateway_resource" "portal_organizations_current" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.portal_organizations.id
  path_part   = "current"
}

resource "aws_api_gateway_resource" "portal_organizations_current_members" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.portal_organizations_current.id
  path_part   = "members"
}

resource "aws_api_gateway_resource" "portal_organizations_current_member_id" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.portal_organizations_current_members.id
  path_part   = "{memberId}"
}

resource "aws_api_gateway_resource" "portal_organizations_current_invitations" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.portal_organizations_current.id
  path_part   = "invitations"
}

resource "aws_api_gateway_resource" "portal_organizations_current_api_keys" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.portal_organizations_current.id
  path_part   = "api-keys"
}

resource "aws_api_gateway_resource" "portal_organizations_current_api_key_id" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.portal_organizations_current_api_keys.id
  path_part   = "{keyId}"
}

resource "aws_api_gateway_resource" "organizations_integrations" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.organizations.id
  path_part   = "settings"
}

resource "aws_api_gateway_resource" "organization_billing" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.organizations.id
  path_part   = "billing"
}

resource "aws_api_gateway_resource" "organization_billing_checkout_session" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.organization_billing.id
  path_part   = "checkout-session"
}

resource "aws_api_gateway_resource" "organization_billing_plan_change" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.organization_billing.id
  path_part   = "plan-change"
}

resource "aws_api_gateway_resource" "organization_billing_portal_session" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.organization_billing.id
  path_part   = "portal-session"
}

resource "aws_api_gateway_resource" "organization_billing_subscription" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.organization_billing.id
  path_part   = "subscription"
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

resource "aws_api_gateway_resource" "ops_form990" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.ops.id
  path_part   = "form990"
}

resource "aws_api_gateway_resource" "ops_form990_runs" {
  rest_api_id = aws_api_gateway_rest_api.irs_api.id
  parent_id   = aws_api_gateway_resource.ops_form990.id
  path_part   = "runs"
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

locals {
  browser_cors_allowed_headers = "Content-Type,Authorization,X-Portal-Account-Id,X-Portal-Workspace-Id"
  browser_cors_allowed_methods = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
  browser_cors_resource_ids = {
    auth_register                            = aws_api_gateway_resource.auth_register.id
    auth_login                               = aws_api_gateway_resource.auth_login.id
    auth_me                                  = aws_api_gateway_resource.auth_me.id
    plans                                    = aws_api_gateway_resource.plans.id
    portal_organizations                     = aws_api_gateway_resource.portal_organizations.id
    portal_organizations_current_members     = aws_api_gateway_resource.portal_organizations_current_members.id
    portal_organizations_current_invitations = aws_api_gateway_resource.portal_organizations_current_invitations.id
    portal_organizations_current_member_id   = aws_api_gateway_resource.portal_organizations_current_member_id.id
    portal_organizations_current_api_keys    = aws_api_gateway_resource.portal_organizations_current_api_keys.id
    portal_organizations_current_api_key_id  = aws_api_gateway_resource.portal_organizations_current_api_key_id.id
    organizations_integrations               = aws_api_gateway_resource.organizations_integrations.id
    organization_billing_checkout_session    = aws_api_gateway_resource.organization_billing_checkout_session.id
    organization_billing_plan_change         = aws_api_gateway_resource.organization_billing_plan_change.id
    organization_billing_portal_session      = aws_api_gateway_resource.organization_billing_portal_session.id
    organization_billing_subscription        = aws_api_gateway_resource.organization_billing_subscription.id
  }
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

resource "aws_api_gateway_method" "post_auth_register" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.auth_register.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "post_auth_login" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.auth_login.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "get_auth_me" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.auth_me.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "post_oauth_token" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.oauth_token.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "post_webhooks_stripe" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.webhooks_stripe.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "post_admin_accounts" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.admin_accounts.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "get_admin_accounts" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.admin_accounts.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "get_admin_account_id" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.admin_account_id.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "patch_admin_account_id" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.admin_account_id.id
  http_method   = "PATCH"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "get_admin_account_subscription" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.admin_account_subscription.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "put_admin_account_subscription" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.admin_account_subscription.id
  http_method   = "PUT"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "post_admin_account_suspend" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.admin_account_suspend.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "post_admin_account_activate" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.admin_account_activate.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "post_admin_account_api_keys" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.admin_account_api_keys.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "get_admin_account_api_keys" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.admin_account_api_keys.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "delete_admin_account_api_key_id" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.admin_account_api_key_id.id
  http_method   = "DELETE"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "post_admin_account_api_key_rotate" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.admin_account_api_key_rotate.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "post_admin_account_oauth_clients" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.admin_account_oauth_clients.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "get_admin_account_oauth_clients" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.admin_account_oauth_clients.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "delete_admin_account_oauth_client_id" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.admin_account_oauth_client_id.id
  http_method   = "DELETE"
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

resource "aws_api_gateway_integration" "lambda_post_auth_register_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.auth_register.id
  http_method             = aws_api_gateway_method.post_auth_register.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.query.invoke_arn
}

resource "aws_api_gateway_integration" "lambda_post_auth_login_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.auth_login.id
  http_method             = aws_api_gateway_method.post_auth_login.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.query.invoke_arn
}

resource "aws_api_gateway_integration" "lambda_get_auth_me_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.auth_me.id
  http_method             = aws_api_gateway_method.get_auth_me.http_method
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

resource "aws_api_gateway_integration" "lambda_webhooks_stripe_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.webhooks_stripe.id
  http_method             = aws_api_gateway_method.post_webhooks_stripe.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.query.invoke_arn
}

resource "aws_api_gateway_integration" "lambda_post_admin_accounts_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.admin_accounts.id
  http_method             = aws_api_gateway_method.post_admin_accounts.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.query.invoke_arn
}

resource "aws_api_gateway_integration" "lambda_get_admin_accounts_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.admin_accounts.id
  http_method             = aws_api_gateway_method.get_admin_accounts.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.query.invoke_arn
}

resource "aws_api_gateway_integration" "lambda_get_admin_account_id_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.admin_account_id.id
  http_method             = aws_api_gateway_method.get_admin_account_id.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.query.invoke_arn
}

resource "aws_api_gateway_integration" "lambda_patch_admin_account_id_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.admin_account_id.id
  http_method             = aws_api_gateway_method.patch_admin_account_id.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.query.invoke_arn
}

resource "aws_api_gateway_integration" "lambda_get_admin_account_subscription_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.admin_account_subscription.id
  http_method             = aws_api_gateway_method.get_admin_account_subscription.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.query.invoke_arn
}

resource "aws_api_gateway_integration" "lambda_put_admin_account_subscription_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.admin_account_subscription.id
  http_method             = aws_api_gateway_method.put_admin_account_subscription.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.query.invoke_arn
}

resource "aws_api_gateway_integration" "lambda_post_admin_account_suspend_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.admin_account_suspend.id
  http_method             = aws_api_gateway_method.post_admin_account_suspend.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.query.invoke_arn
}

resource "aws_api_gateway_integration" "lambda_post_admin_account_activate_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.admin_account_activate.id
  http_method             = aws_api_gateway_method.post_admin_account_activate.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.query.invoke_arn
}

resource "aws_api_gateway_integration" "lambda_post_admin_account_api_keys_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.admin_account_api_keys.id
  http_method             = aws_api_gateway_method.post_admin_account_api_keys.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.query.invoke_arn
}

resource "aws_api_gateway_integration" "lambda_get_admin_account_api_keys_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.admin_account_api_keys.id
  http_method             = aws_api_gateway_method.get_admin_account_api_keys.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.query.invoke_arn
}

resource "aws_api_gateway_integration" "lambda_delete_admin_account_api_key_id_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.admin_account_api_key_id.id
  http_method             = aws_api_gateway_method.delete_admin_account_api_key_id.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.query.invoke_arn
}

resource "aws_api_gateway_integration" "lambda_post_admin_account_api_key_rotate_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.admin_account_api_key_rotate.id
  http_method             = aws_api_gateway_method.post_admin_account_api_key_rotate.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.query.invoke_arn
}

resource "aws_api_gateway_integration" "lambda_post_admin_account_oauth_clients_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.admin_account_oauth_clients.id
  http_method             = aws_api_gateway_method.post_admin_account_oauth_clients.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.query.invoke_arn
}

resource "aws_api_gateway_integration" "lambda_get_admin_account_oauth_clients_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.admin_account_oauth_clients.id
  http_method             = aws_api_gateway_method.get_admin_account_oauth_clients.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.query.invoke_arn
}

resource "aws_api_gateway_integration" "lambda_delete_admin_account_oauth_client_id_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.admin_account_oauth_client_id.id
  http_method             = aws_api_gateway_method.delete_admin_account_oauth_client_id.http_method
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

resource "aws_api_gateway_method" "post_nonprofits_verify" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.nonprofits_verify.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "get_nonprofits_ein" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.nonprofits_ein.id
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

resource "aws_api_gateway_integration" "lambda_nonprofits_verify_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.nonprofits_verify.id
  http_method             = aws_api_gateway_method.post_nonprofits_verify.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.query.invoke_arn
}

resource "aws_api_gateway_integration" "lambda_get_nonprofits_ein_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.nonprofits_ein.id
  http_method             = aws_api_gateway_method.get_nonprofits_ein.http_method
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

resource "aws_api_gateway_method" "get_plans" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.plans.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "post_portal_organizations" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.portal_organizations.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "get_portal_organizations_current_members" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.portal_organizations_current_members.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "post_portal_organizations_current_invitations" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.portal_organizations_current_invitations.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "get_portal_organizations_current_api_keys" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.portal_organizations_current_api_keys.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "post_portal_organizations_current_api_keys" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.portal_organizations_current_api_keys.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "patch_portal_organizations_current_member_id" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.portal_organizations_current_member_id.id
  http_method   = "PATCH"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "delete_portal_organizations_current_member_id" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.portal_organizations_current_member_id.id
  http_method   = "DELETE"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "delete_portal_organizations_current_api_key_id" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.portal_organizations_current_api_key_id.id
  http_method   = "DELETE"
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

resource "aws_api_gateway_method" "post_organization_billing_checkout_session" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.organization_billing_checkout_session.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "post_organization_billing_plan_change" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.organization_billing_plan_change.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "post_organization_billing_portal_session" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.organization_billing_portal_session.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "get_organization_billing_subscription" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.organization_billing_subscription.id
  http_method   = "GET"
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

resource "aws_api_gateway_method" "post_ops_form990_runs" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = aws_api_gateway_resource.ops_form990_runs.id
  http_method   = "POST"
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

resource "aws_api_gateway_method" "options_browser_cors" {
  for_each = local.browser_cors_resource_ids

  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  resource_id   = each.value
  http_method   = "OPTIONS"
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

resource "aws_api_gateway_integration" "lambda_get_plans_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.plans.id
  http_method             = aws_api_gateway_method.get_plans.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.query.invoke_arn
}

resource "aws_api_gateway_integration" "lambda_post_portal_organizations_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.portal_organizations.id
  http_method             = aws_api_gateway_method.post_portal_organizations.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.query.invoke_arn
}

resource "aws_api_gateway_integration" "lambda_get_portal_organizations_current_members_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.portal_organizations_current_members.id
  http_method             = aws_api_gateway_method.get_portal_organizations_current_members.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.query.invoke_arn
}

resource "aws_api_gateway_integration" "lambda_post_portal_organizations_current_invitations_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.portal_organizations_current_invitations.id
  http_method             = aws_api_gateway_method.post_portal_organizations_current_invitations.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.query.invoke_arn
}

resource "aws_api_gateway_integration" "lambda_get_portal_organizations_current_api_keys_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.portal_organizations_current_api_keys.id
  http_method             = aws_api_gateway_method.get_portal_organizations_current_api_keys.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.query.invoke_arn
}

resource "aws_api_gateway_integration" "lambda_post_portal_organizations_current_api_keys_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.portal_organizations_current_api_keys.id
  http_method             = aws_api_gateway_method.post_portal_organizations_current_api_keys.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.query.invoke_arn
}

resource "aws_api_gateway_integration" "lambda_patch_portal_organizations_current_member_id_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.portal_organizations_current_member_id.id
  http_method             = aws_api_gateway_method.patch_portal_organizations_current_member_id.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.query.invoke_arn
}

resource "aws_api_gateway_integration" "lambda_delete_portal_organizations_current_member_id_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.portal_organizations_current_member_id.id
  http_method             = aws_api_gateway_method.delete_portal_organizations_current_member_id.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.query.invoke_arn
}

resource "aws_api_gateway_integration" "lambda_delete_portal_organizations_current_api_key_id_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.portal_organizations_current_api_key_id.id
  http_method             = aws_api_gateway_method.delete_portal_organizations_current_api_key_id.http_method
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

resource "aws_api_gateway_integration" "lambda_post_organization_billing_checkout_session_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.organization_billing_checkout_session.id
  http_method             = aws_api_gateway_method.post_organization_billing_checkout_session.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.query.invoke_arn
}

resource "aws_api_gateway_integration" "lambda_post_organization_billing_plan_change_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.organization_billing_plan_change.id
  http_method             = aws_api_gateway_method.post_organization_billing_plan_change.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.query.invoke_arn
}

resource "aws_api_gateway_integration" "lambda_post_organization_billing_portal_session_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.organization_billing_portal_session.id
  http_method             = aws_api_gateway_method.post_organization_billing_portal_session.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.query.invoke_arn
}

resource "aws_api_gateway_integration" "lambda_get_organization_billing_subscription_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.organization_billing_subscription.id
  http_method             = aws_api_gateway_method.get_organization_billing_subscription.http_method
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

resource "aws_api_gateway_integration" "lambda_ops_form990_runs_integration" {
  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = aws_api_gateway_resource.ops_form990_runs.id
  http_method             = aws_api_gateway_method.post_ops_form990_runs.http_method
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

resource "aws_api_gateway_integration" "lambda_options_browser_cors_integration" {
  for_each = local.browser_cors_resource_ids

  rest_api_id             = aws_api_gateway_rest_api.irs_api.id
  resource_id             = each.value
  http_method             = aws_api_gateway_method.options_browser_cors[each.key].http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.query.invoke_arn
}

resource "aws_api_gateway_gateway_response" "default_4xx_cors" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  response_type = "DEFAULT_4XX"

  response_parameters = {
    "gatewayresponse.header.Access-Control-Allow-Origin"  = "method.request.header.Origin"
    "gatewayresponse.header.Access-Control-Allow-Headers" = "'${local.browser_cors_allowed_headers}'"
    "gatewayresponse.header.Access-Control-Allow-Methods" = "'${local.browser_cors_allowed_methods}'"
    "gatewayresponse.header.Vary"                         = "'Origin'"
  }
}

resource "aws_api_gateway_gateway_response" "default_5xx_cors" {
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  response_type = "DEFAULT_5XX"

  response_parameters = {
    "gatewayresponse.header.Access-Control-Allow-Origin"  = "method.request.header.Origin"
    "gatewayresponse.header.Access-Control-Allow-Headers" = "'${local.browser_cors_allowed_headers}'"
    "gatewayresponse.header.Access-Control-Allow-Methods" = "'${local.browser_cors_allowed_methods}'"
    "gatewayresponse.header.Vary"                         = "'Origin'"
  }
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
    aws_api_gateway_integration.lambda_post_auth_register_integration,
    aws_api_gateway_integration.lambda_post_auth_login_integration,
    aws_api_gateway_integration.lambda_get_auth_me_integration,
    aws_api_gateway_integration.lambda_oauth_token_integration,
    aws_api_gateway_integration.lambda_webhooks_stripe_integration,
    aws_api_gateway_integration.lambda_post_admin_accounts_integration,
    aws_api_gateway_integration.lambda_get_admin_accounts_integration,
    aws_api_gateway_integration.lambda_get_admin_account_id_integration,
    aws_api_gateway_integration.lambda_patch_admin_account_id_integration,
    aws_api_gateway_integration.lambda_get_admin_account_subscription_integration,
    aws_api_gateway_integration.lambda_put_admin_account_subscription_integration,
    aws_api_gateway_integration.lambda_post_admin_account_suspend_integration,
    aws_api_gateway_integration.lambda_post_admin_account_activate_integration,
    aws_api_gateway_integration.lambda_post_admin_account_api_keys_integration,
    aws_api_gateway_integration.lambda_get_admin_account_api_keys_integration,
    aws_api_gateway_integration.lambda_delete_admin_account_api_key_id_integration,
    aws_api_gateway_integration.lambda_post_admin_account_api_key_rotate_integration,
    aws_api_gateway_integration.lambda_post_admin_account_oauth_clients_integration,
    aws_api_gateway_integration.lambda_get_admin_account_oauth_clients_integration,
    aws_api_gateway_integration.lambda_delete_admin_account_oauth_client_id_integration,
    aws_api_gateway_integration.lambda_verify_batch_integration,
    aws_api_gateway_integration.lambda_get_organizations_integrations_integration,
    aws_api_gateway_integration.lambda_put_organizations_integrations_integration,
    aws_api_gateway_integration.lambda_post_organization_billing_checkout_session_integration,
    aws_api_gateway_integration.lambda_post_organization_billing_plan_change_integration,
    aws_api_gateway_integration.lambda_post_organization_billing_portal_session_integration,
    aws_api_gateway_integration.lambda_get_organization_billing_subscription_integration,
    aws_api_gateway_integration.lambda_nonprofits_search_integration,
    aws_api_gateway_integration.lambda_nonprofits_verify_integration,
    aws_api_gateway_integration.lambda_get_nonprofits_ein_integration,
    aws_api_gateway_integration.lambda_nonprofits_sources_integration,
    aws_api_gateway_integration.lambda_nonprofits_source_name_integration,
    aws_api_gateway_integration.lambda_nonprofits_compliance_integration,
    aws_api_gateway_integration.lambda_nonprofits_federal_awards_integration,
    aws_api_gateway_integration.lambda_get_plans_integration,
    aws_api_gateway_integration.lambda_post_portal_organizations_integration,
    aws_api_gateway_integration.lambda_get_portal_organizations_current_members_integration,
    aws_api_gateway_integration.lambda_post_portal_organizations_current_invitations_integration,
    aws_api_gateway_integration.lambda_get_portal_organizations_current_api_keys_integration,
    aws_api_gateway_integration.lambda_post_portal_organizations_current_api_keys_integration,
    aws_api_gateway_integration.lambda_patch_portal_organizations_current_member_id_integration,
    aws_api_gateway_integration.lambda_delete_portal_organizations_current_member_id_integration,
    aws_api_gateway_integration.lambda_delete_portal_organizations_current_api_key_id_integration,
    aws_api_gateway_integration.lambda_ops_ingest_runs_integration,
    aws_api_gateway_integration.lambda_ops_ingest_run_id_integration,
    aws_api_gateway_integration.lambda_ops_ingest_run_filings_integration,
    aws_api_gateway_integration.lambda_ops_form990_runs_integration,
    aws_api_gateway_integration.lambda_ops_refresh_runs_integration,
    aws_api_gateway_integration.lambda_ops_refresh_run_id_integration,
    aws_api_gateway_integration.lambda_ops_refresh_run_eins_integration,
    aws_api_gateway_integration.lambda_ops_nonprofit_pipeline_status_integration,
    aws_api_gateway_integration.lambda_options_browser_cors_integration
  ]

  rest_api_id = aws_api_gateway_rest_api.irs_api.id

  triggers = {
    redeployment = filesha1("${path.module}/aws_api_gateway.tf")
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_stage" "environment" {
  deployment_id = aws_api_gateway_deployment.deployment.id
  rest_api_id   = aws_api_gateway_rest_api.irs_api.id
  stage_name    = var.environment
}
