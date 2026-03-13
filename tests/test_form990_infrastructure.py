from pathlib import Path


def test_form990_raw_source_prefix_variable_exists():
    content = Path("infrastructure/variables.tf").read_text(encoding="utf-8")
    assert 'variable "form990_raw_source_prefix"' in content


def test_irs_data_bucket_versioning_is_not_enabled():
    content = Path("infrastructure/aws_s3.tf").read_text(encoding="utf-8")
    assert 'resource "aws_s3_bucket_versioning" "irs_data"' in content
    assert 'status = "Suspended"' in content
