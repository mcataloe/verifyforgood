from pathlib import Path


def test_main_tf_defines_standardized_naming_locals_and_compatibility_map():
    content = Path("infrastructure/main.tf").read_text(encoding="utf-8")

    assert 'namespace        = "n8x4"' in content
    assert 'platform         = "verification"' in content
    assert 'region_short     = "use1"' in content
    assert "stable_resource_prefix" in content
    assert "data_catalog_prefix" in content
    assert 'standardized_resource_names = {' in content
    assert 'legacy_resource_names = {' in content
    assert 'resource_names = {' in content
    assert 'lambda_function_names = {' in content
    assert 'queue_names = {' in content
    assert 'scheduled_workflow_names = {' in content
    assert 'platform_common_tags = merge({' in content
    assert 'PlatformNamespace = "verification_platform"' in content
    assert 'PlatformDomain    = "organization_verification"' in content
    assert "common_tags = local.platform_common_tags" in content
    assert 'resource_name_strategy == "standardized"' in content
    assert "resource identity stays stable across public-brand changes" in content


def test_main_tf_routes_named_resources_through_centralized_locals():
    content = Path("infrastructure/main.tf").read_text(encoding="utf-8")

    assert "source_data_bucket_name" in content and "local.resource_names.source_data_bucket" in content
    assert "athena_results_bucket_name" in content and "local.resource_names.athena_results_bucket" in content
    assert "profile_table_name" in content and "local.resource_names.profile_table" in content
    assert "organization_settings_table_name" in content and "local.resource_names.organization_settings_table" in content
    assert "control_plane_table_name" in content and "local.resource_names.control_plane_table" in content
    assert "ecs_cluster_name" in content and "local.resource_names.ecs_cluster" in content
    assert "athena_workgroup_resource_name" in content and "local.resource_names.athena_workgroup" in content
    assert "api_gateway_name" in content and "local.resource_names.api_gateway" in content
    assert "lambda_role_name" in content and "local.resource_names.lambda_role" in content
    assert "monthly_ingest_state_machine_name" in content and "local.resource_names.monthly_ingest_state_machine" in content
    assert "monthly_ingest_state_machine_role_name" in content and "local.resource_names.monthly_ingest_state_machine_role" in content
    assert "monthly_ingest_schedule_rule_name" in content and "local.resource_names.monthly_ingest_schedule_rule" in content
    assert "glue_database_name" in content and "local.data_catalog_prefix" in content
    assert "ingest_lambda_name" in content and "local.lambda_function_names.regulatory_data_ingestion" in content
    assert "query_lambda_name" in content and "local.lambda_function_names.organization_verification_api" in content
    assert "form990_work_queue_name" in content and "local.queue_names.regulatory_filing_work" in content
    assert "form990_schedule_rule_name" in content and "local.scheduled_workflow_names.monthly_filing_ingestion" in content


def test_lambda_and_schedule_resources_use_neutral_capability_maps():
    content = Path("infrastructure/aws_lambda.tf").read_text(encoding="utf-8")

    assert "local.lambda_function_names.regulatory_data_ingestion" in content
    assert "local.lambda_function_names.organization_verification_api" in content
    assert "local.lambda_function_names.platform_refresh" in content
    assert "local.lambda_function_names.regulatory_filing_ingestion" in content
    assert "local.lambda_function_names.regulatory_filing_orchestrator" in content
    assert "local.lambda_function_names.regulatory_filing_worker" in content
    assert "local.queue_names.regulatory_filing_work_dead_letter" in content
    assert "local.queue_names.regulatory_filing_work" in content
    assert "local.scheduled_workflow_names.regulatory_data_ingestion" in content
    assert "local.scheduled_workflow_names.platform_refresh" in content
    assert "local.scheduled_workflow_names.monthly_filing_ingestion" in content


def test_variables_expose_migration_safe_naming_controls():
    content = Path("infrastructure/variables.tf").read_text(encoding="utf-8")

    assert 'variable "resource_name_strategy"' in content
    assert 'default     = "legacy"' in content
    assert 'contains(["legacy", "standardized"], var.resource_name_strategy)' in content
    assert 'variable "resource_name_overrides"' in content


def test_backend_configs_document_legacy_bootstrap_exception():
    dev_backend = Path("infrastructure/backend-dev.hcl").read_text(encoding="utf-8")
    prod_backend = Path("infrastructure/backend-prod.hcl").read_text(encoding="utf-8")

    assert "Backend bootstrap resources remain pinned to legacy names" in dev_backend
    assert "Terraform resource naming strategy toggle" in dev_backend
    assert "Backend bootstrap resources remain pinned to legacy names" in prod_backend
    assert "Terraform resource naming strategy toggle" in prod_backend


def test_examples_document_legacy_default_for_safe_rollout():
    shared_example = Path("infrastructure/terraform.shared.tfvars.example").read_text(encoding="utf-8")
    root_example = Path("infrastructure/terraform.tfvars.example").read_text(encoding="utf-8")

    assert 'resource_name_strategy = "legacy"' in shared_example
    assert 'resource_name_strategy     = "legacy"' in root_example


def test_infrastructure_naming_docs_capture_mapping_and_exceptions():
    content = Path("docs/infrastructure-naming-normalization.md").read_text(encoding="utf-8")

    assert "Legacy To Neutral Mapping" in content
    assert "`legacy_name_prefix`" in content
    assert "`lambda_function_names.regulatory_data_ingestion`" in content
    assert "`charitystatusapi-dev` backend bucket/table" in content
    assert "4. Customer-facing/public contract" in content


def test_readmes_link_to_infrastructure_naming_normalization_doc():
    root_readme = Path("README.md").read_text(encoding="utf-8")
    infra_readme = Path("infrastructure/README.md").read_text(encoding="utf-8")

    assert "docs/infrastructure-naming-normalization.md" in root_readme
    assert "docs/infrastructure-naming-normalization.md" in infra_readme
