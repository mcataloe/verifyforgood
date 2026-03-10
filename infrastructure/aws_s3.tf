#############################################
# S3 BUCKET FOR IRS DATA
#############################################

resource "aws_s3_bucket" "irs_data" {
  bucket = "irs-nonprofit-datasets-${random_id.rand.hex}"
}

resource "random_id" "rand" {
  byte_length = 4
}