from pathlib import Path


def test_form990_raw_source_prefix_variable_exists():
    content = Path("infrastructure/variables.tf").read_text(encoding="utf-8")
    assert 'variable "form990_raw_source_prefix"' in content


def test_irs_data_bucket_versioning_is_not_enabled():
    content = Path("infrastructure/aws_s3.tf").read_text(encoding="utf-8")
    assert 'resource "aws_s3_bucket_versioning" "irs_data"' in content
    assert 'status = "Suspended"' in content


def test_form990_ecs_envs_include_required_paths_and_run_task_wiring():
    api_content = Path("infrastructure/aws_api_ecs.tf").read_text(encoding="utf-8")
    ecs_content = Path("infrastructure/aws_ecs.tf").read_text(encoding="utf-8")

    assert "FORM990_RUN_TASK_CLUSTER_ARN" in api_content
    assert "FORM990_RUN_TASK_DEFINITION_ARN" in api_content
    assert "FORM990_RUN_TASK_CONTAINER_NAME" in api_content
    assert "FORM990_RUN_TASK_SUBNET_IDS" in api_content
    assert "FORM990_RUN_TASK_SECURITY_GROUP_IDS" in api_content
    assert '"ecs:RunTask"' in api_content
    assert '"iam:PassRole"' in api_content


def test_form990_source_mode_defaults_to_static_manifest():
    content = Path("infrastructure/variables.tf").read_text(encoding="utf-8")
    assert 'default     = "static_manifest"' in content


def test_form990_next_year_generation_defaults_enabled():
    content = Path("infrastructure/variables.tf").read_text(encoding="utf-8")
    assert 'variable "form990_enable_next_year_generation"' in content
    section = content.split('variable "form990_enable_next_year_generation"', 1)[1].split('variable "', 1)[0]
    assert "default     = true" in section


def test_form990_static_manifest_is_packaged_with_form990_code():
    assert Path(
        "backend/ingest/federal/src/verification/backend/ingest/federal/form990/Form990Links.txt"
    ).exists()


def test_ingest_task_policies_remove_legacy_s3_bucket_access():
    content = Path("infrastructure/aws_ecs.tf").read_text(encoding="utf-8")
    assert '"s3:GetObject"' not in content
    assert '"s3:PutObject"' not in content
    assert '"s3:ListBucket"' not in content


def test_monthly_ingest_worker_packaging_and_task_access_exist():
    dockerfile = Path("backend/ingest/federal/Dockerfile").read_text(encoding="utf-8")
    ecs_content = Path("infrastructure/aws_ecs.tf").read_text(encoding="utf-8")

    assert "verification.backend.ingest.federal.cli" in dockerfile
    assert 'CMD ["monthly-worker"]' in dockerfile
    assert 'command    = ["ecs-run"]' in ecs_content
    assert 'entryPoint = ["python", "-m", "verification.backend.ingest.federal.cli"]' in ecs_content
    assert 'WORKSPACE_PATH' in ecs_content
    assert 'STRICT_MODE' in ecs_content
    assert 'MAX_ARCHIVES' in ecs_content
    assert 'LOG_LEVEL' in ecs_content
    assert '"s3:GetObject"' not in ecs_content
    assert '"s3:PutObject"' not in ecs_content
    assert '"s3:ListBucket"' not in ecs_content


def test_monthly_and_persistence_runtime_entrypoints_are_backend_owned():
    monthly_worker = Path(
        "backend/ingest/federal/src/verification/backend/ingest/federal/monthly/worker.py"
    ).read_text(encoding="utf-8")
    persistence = Path(
        "backend/ingest/federal/src/verification/backend/ingest/federal/persistence.py"
    ).read_text(encoding="utf-8")

    assert "Backend-owned monthly ECS worker runtime entrypoint." in monthly_worker
    assert "run_form990_monthly_processing_task" in monthly_worker
    assert "Backend-owned runtime import root for nonprofit ingest persistence." in persistence
    assert "build_form990_nonprofit_persistence_service" in persistence


def test_dev_form990_defaults_use_orchestrated_current_year_scope():
    content = Path("infrastructure/terraform-dev.tfvars").read_text(encoding="utf-8")
    assert 'form990_execution_mode' in content
    assert '"orchestrated"' in content
    assert "form990_incremental_year_window" in content
    assert "= 1" in content

