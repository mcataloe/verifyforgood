from pathlib import Path


def test_main_tf_defines_standardized_naming_locals_and_compatibility_map():
    content = Path("infrastructure/main.tf").read_text(encoding="utf-8")

    assert 'namespace        = "n8x4"' in content
    assert 'platform         = "verification"' in content
    assert 'region_short     = "use1"' in content
    assert 'standardized_resource_names = {' in content
    assert 'legacy_resource_names = {' in content
    assert 'resource_names = {' in content
    assert 'resource_name_strategy == "standardized"' in content
    assert "branding changes such as CharityStatusAPI -> VerifyForGood" in content


def test_main_tf_routes_named_resources_through_centralized_locals():
    content = Path("infrastructure/main.tf").read_text(encoding="utf-8")

    assert "source_data_bucket_name" in content and "local.resource_names.source_data_bucket" in content
    assert "athena_results_bucket_name" in content and "local.resource_names.athena_results_bucket" in content
    assert "profile_table_name" in content and "local.resource_names.profile_table" in content
    assert "organization_settings_table_name" in content and "local.resource_names.organization_settings_table" in content
    assert "control_plane_table_name" in content and "local.resource_names.control_plane_table" in content
    assert "athena_workgroup_resource_name" in content and "local.resource_names.athena_workgroup" in content
    assert "api_gateway_name" in content and "local.resource_names.api_gateway" in content
    assert "lambda_role_name" in content and "local.resource_names.lambda_role" in content
    assert "form990_work_queue_name" in content and "local.resource_names.form990_work_queue" in content


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
