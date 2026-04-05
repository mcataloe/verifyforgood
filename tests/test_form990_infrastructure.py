from pathlib import Path


def test_form990_raw_source_prefix_variable_exists():
    content = Path("infrastructure/variables.tf").read_text(encoding="utf-8")
    assert 'variable "form990_raw_source_prefix"' in content


def test_irs_data_bucket_versioning_is_not_enabled():
    content = Path("infrastructure/aws_s3.tf").read_text(encoding="utf-8")
    assert 'resource "aws_s3_bucket_versioning" "irs_data"' in content
    assert 'status = "Suspended"' in content


def test_form990_lambda_envs_include_required_paths_and_queue():
    content = Path("infrastructure/aws_lambda.tf").read_text(encoding="utf-8")
    assert "FORM990_RAW_SOURCE_PREFIX" in content
    assert "FORM990_MANIFEST_PREFIX" in content
    assert "FORM990_ENABLE_NEXT_YEAR_GENERATION" in content
    assert "OPS_METADATA_BUCKET" in content
    assert "FORM990_WORK_QUEUE_URL" in content


def test_form990_source_mode_defaults_to_static_manifest():
    content = Path("infrastructure/variables.tf").read_text(encoding="utf-8")
    assert 'default     = "static_manifest"' in content


def test_form990_next_year_generation_defaults_enabled():
    content = Path("infrastructure/variables.tf").read_text(encoding="utf-8")
    assert 'variable "form990_enable_next_year_generation"' in content
    section = content.split('variable "form990_enable_next_year_generation"', 1)[1].split('variable "', 1)[0]
    assert "default     = true" in section


def test_form990_static_manifest_is_packaged_with_form990_code():
    assert Path("infrastructure/charity_status/form990/Form990Links.txt").exists()


def test_iam_policy_includes_s3_and_sqs_access_for_worker_flow():
    content = Path("infrastructure/aws_iam.tf").read_text(encoding="utf-8")
    assert '"s3:*"' in content
    assert '"sqs:*"' in content


def test_monthly_ingest_worker_packaging_and_task_access_exist():
    dockerfile = Path("backend/ingest-task/Dockerfile").read_text(encoding="utf-8")
    ecs_content = Path("infrastructure/aws_ecs.tf").read_text(encoding="utf-8")

    assert "charity_status_backend.ingest_task.cli" in dockerfile
    assert 'CMD ["monthly-worker"]' in dockerfile
    assert 'command    = ["ecs-run"]' in ecs_content
    assert 'entryPoint = ["python", "-m", "charity_status_backend.ingest_task.cli"]' in ecs_content
    assert 'WORKSPACE_PATH' in ecs_content
    assert 'STRICT_MODE' in ecs_content
    assert 'MAX_ARCHIVES' in ecs_content
    assert 'LOG_LEVEL' in ecs_content
    assert '"s3:GetObject"' in ecs_content
    assert '"s3:PutObject"' in ecs_content
    assert '"s3:ListBucket"' in ecs_content


def test_monthly_and_persistence_runtime_entrypoints_are_backend_owned_behind_shims():
    monthly_worker = Path("infrastructure/monthly_ingest_worker.py").read_text(encoding="utf-8")
    persistence = Path("infrastructure/nonprofit_ingest_persistence.py").read_text(encoding="utf-8")

    assert "backend-owned monthly ECS worker runtime" in monthly_worker
    assert "charity_status_backend.ingest_task.monthly.worker" in monthly_worker
    assert "backend-owned nonprofit ingest persistence" in persistence
    assert "charity_status_backend.ingest_task.persistence" in persistence


def test_dev_form990_defaults_use_orchestrated_current_year_scope():
    content = Path("infrastructure/terraform-dev.tfvars").read_text(encoding="utf-8")
    assert 'form990_execution_mode' in content
    assert '"orchestrated"' in content
    assert "form990_incremental_year_window" in content
    assert "= 1" in content
