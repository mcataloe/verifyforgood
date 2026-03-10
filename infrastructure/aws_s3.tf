#############################################
# S3 BUCKET FOR IRS DATA
#############################################

resource "aws_s3_bucket" "irs_data" {
  bucket = var.source_data_bucket_name
}