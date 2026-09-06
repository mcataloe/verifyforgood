locals {
  customer_documents_bucket_name = "${local.namespace}-${local.platform}-customer-documents-${local.environment_slug}-${local.region_short}"
}

resource "aws_s3_bucket" "customer_documents" {
  count = var.customer_documents_bucket_enabled ? 1 : 0

  bucket        = local.customer_documents_bucket_name
  force_destroy = var.customer_documents_force_destroy

  tags = merge(local.platform_common_tags, {
    Purpose = "customer-document-uploads"
  })
}

resource "aws_s3_bucket_public_access_block" "customer_documents" {
  count = var.customer_documents_bucket_enabled ? 1 : 0

  bucket                  = aws_s3_bucket.customer_documents[0].id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "customer_documents" {
  count = var.customer_documents_bucket_enabled ? 1 : 0

  bucket = aws_s3_bucket.customer_documents[0].id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "customer_documents" {
  count = var.customer_documents_bucket_enabled ? 1 : 0

  bucket = aws_s3_bucket.customer_documents[0].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "customer_documents" {
  count = var.customer_documents_bucket_enabled ? 1 : 0

  bucket = aws_s3_bucket.customer_documents[0].id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "customer_documents" {
  count = var.customer_documents_bucket_enabled ? 1 : 0

  bucket = aws_s3_bucket.customer_documents[0].id

  rule {
    id     = "abort-incomplete-multipart-uploads"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  # Deliberately no object-expiration policy yet. Retention cannot be safely
  # chosen until customer/user ownership and tenant-partitioning rules exist.
}

resource "aws_iam_role_policy" "api_customer_documents" {
  count = var.api_ecs_enabled && var.customer_documents_bucket_enabled ? 1 : 0

  name = "${local.api_task_role_name}-customer-documents"
  role = aws_iam_role.api_task[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "CustomerDocumentBucketMetadata"
        Effect = "Allow"
        Action = [
          "s3:GetBucketLocation",
          "s3:ListBucket"
        ]
        Resource = [aws_s3_bucket.customer_documents[0].arn]
      },
      {
        Sid    = "CustomerDocumentObjectAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = ["${aws_s3_bucket.customer_documents[0].arn}/*"]
      }
    ]
  })
}

resource "aws_iam_role_policy" "api_bedrock_runtime" {
  count = var.api_ecs_enabled && var.bedrock_runtime_access_enabled ? 1 : 0

  name = "${local.api_task_role_name}-bedrock-runtime"
  role = aws_iam_role.api_task[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "InvokeApprovedBedrockModels"
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = var.bedrock_allowed_model_arns
      }
    ]
  })
}
