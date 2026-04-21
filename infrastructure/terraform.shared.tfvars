base_name              = "charitystatusapi"
aws_region             = "us-east-1"
resource_name_strategy = "legacy"
public_brand_name      = "VerifyForGood"
support_email          = "support@verifyforgood.com"
domain                 = "verifyforgood.com"
source_data_prefix     = "eo_bmf/"
athena_workgroup_name  = "irs-eo-bmf"

form990_raw_prefix                       = "form990/raw/"
form990_raw_source_prefix                = "form990/raw-sources/"
form990_metadata_prefix                  = "form990/normalized/metadata/"
form990_manifest_prefix                  = "form990/normalized/manifests/"
form990_metrics_prefix                   = "form990/normalized/metrics/"
form990_governance_prefix                = "form990/normalized/governance/"
form990_quality_prefix                   = "form990/normalized/quality/"
form990_relationships_prefix             = "form990/normalized/relationships/"
form990_index_url                        = ""
form990_index_urls                       = ""
form990_index_fetch_timeout_seconds      = 60
form990_default_download_raw             = true
form990_run_mode                         = "incremental"
form990_batch_size                       = 100
form990_retry_count                      = 2
form990_source_catalog_json              = ""
form990_incremental_year_window          = 2
form990_reconciliation_enabled           = true
form990_reconciliation_cadence_days      = 30
form990_target_years                     = ""
form990_last_reconciliation_at           = ""
form990_source_mode                      = "static_manifest"
form990_enable_next_year_generation      = true
form990_irs_downloads_page_url           = "https://www.irs.gov/charities-non-profits/form-990-series-downloads"
form990_zip_fetch_timeout_seconds        = 120
form990_zip_max_xml_file_size_bytes      = 20971520
form990_lambda_timeout_seconds           = 900
form990_lambda_memory_size_mb            = 3072
form990_execution_mode                   = "inline"
form990_chunk_size                       = 250

monthly_ingest_worker_image_tag                   = "latest"
monthly_ingest_task_cpu                           = 2048
monthly_ingest_task_memory                        = 8192
monthly_ingest_task_ephemeral_storage_gib         = 100
monthly_ingest_task_log_retention_days            = 30
api_ecs_enabled                                   = false
api_ecs_image_tag                                 = "latest"
api_ecs_container_name                            = "api"
api_ecs_container_port                            = 8000
api_ecs_task_cpu                                  = 1024
api_ecs_task_memory                               = 2048
api_ecs_desired_count                             = 1
api_ecs_log_retention_days                        = 30
api_ecs_health_check_path                         = "/ready"
api_ecs_health_check_matcher                      = "200-399"
api_ecs_health_check_interval_seconds             = 30
api_ecs_health_check_timeout_seconds              = 5
api_ecs_healthy_threshold                         = 2
api_ecs_unhealthy_threshold                       = 2
api_ecs_health_check_grace_period_seconds         = 60
api_ecs_target_group_deregistration_delay_seconds = 30
api_ecs_secret_arns                               = {}
api_ecs_secret_kms_key_arns                       = []

enrichment_mock_enabled          = false
enrichment_mock_offered          = null
third_party_integrations_enabled = false

integration_candid_enabled            = false
integration_candid_client_id          = ""
integration_charity_navigator_enabled = false

default_require_candid_for_evaluation            = false
default_require_charity_navigator_for_evaluation = false

enrichment_candid_enabled  = false
enrichment_candid_offered  = null
enrichment_candid_endpoint = ""

enrichment_timeout_seconds = 5

enrichment_state_registry_enabled      = true
enrichment_state_registry_offered      = null
enrichment_state_registry_mock_enabled = false
enrichment_state_registry_endpoint     = ""

enrichment_state_registry_colorado_enabled   = true
enrichment_state_registry_colorado_app_token = ""

enrichment_state_registry_kentucky_enabled       = false
enrichment_state_registry_kentucky_companies_url = ""

enrichment_state_business_enabled      = false
enrichment_state_business_offered      = null
enrichment_state_business_mock_enabled = false
enrichment_state_business_endpoint     = ""

enrichment_usaspending_enabled      = false
enrichment_usaspending_offered      = null
enrichment_usaspending_mock_enabled = false
enrichment_usaspending_endpoint     = ""

enrichment_ofac_enabled      = false
enrichment_ofac_offered      = null
enrichment_ofac_mock_enabled = false
enrichment_ofac_endpoint     = ""

search_max_limit                       = 50
search_default_limit                   = 20
api_auth_enabled                       = false
oauth_m2m_enabled                      = false
organization_integration_settings_json = "[]"
tenant_integration_settings_json       = "[]"
stripe_billing_enabled                 = false
stripe_price_ids_json                  = "{}"
free_trial_enabled                     = true
free_trial_duration_days               = 14
free_trial_plan_code                   = "growth"
free_trial_monthly_request_limit       = null
ops_metadata_prefix                    = "ops/"

refresh_mode                     = "refresh_changed"
refresh_batch_size               = 100
refresh_force                    = false
refresh_source_detection_enabled = false

bootstrap_nonprod_override    = false
bootstrap_start_after_ein     = ""
bootstrap_max_batches_per_run = 0

batch_verify_max_size   = 25
root_domain_name        = "charitystatusapi.com"
route53_zone_name       = "charitystatusapi.com."
oauth_token_ttl_seconds = 3600

