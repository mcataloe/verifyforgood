#############################################
# S3 BUCKET FOR IRS DATA
#############################################

resource "aws_s3_bucket" "irs_data" {
  bucket        = local.source_data_bucket_name
  force_destroy = var.environment != "prod"
}

resource "aws_s3_bucket_versioning" "irs_data" {
  bucket = aws_s3_bucket.irs_data.id

  versioning_configuration {
    # Raw IRS ZIP/CSV history is preserved via object keys and manifests, not bucket versioning.
    status = "Suspended"
  }
}
