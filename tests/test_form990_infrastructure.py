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
    assert "OPS_METADATA_BUCKET" in content
    assert "FORM990_WORK_QUEUE_URL" in content


def test_form990_source_mode_defaults_to_static_manifest():
    content = Path("infrastructure/variables.tf").read_text(encoding="utf-8")
    assert 'default     = "static_manifest"' in content


def test_form990_static_manifest_is_packaged_with_form990_code():
    assert Path("infrastructure/charity_status/form990/Form990Links.txt").exists()


def test_iam_policy_includes_s3_and_sqs_access_for_worker_flow():
    content = Path("infrastructure/aws_iam.tf").read_text(encoding="utf-8")
    assert '"s3:*"' in content
    assert '"sqs:*"' in content
