locals {
  monthly_ingest_managed_task_definition_enabled = var.monthly_ingest_state_machine_enabled && trim(var.monthly_ingest_task_definition_arn, " ") == ""
  monthly_ingest_task_execution_role_arn_resolved = trim(var.monthly_ingest_task_execution_role_arn, " ") != "" ? trim(var.monthly_ingest_task_execution_role_arn, " ") : (
    local.monthly_ingest_managed_task_definition_enabled ? aws_iam_role.monthly_ingest_task_execution[0].arn : ""
  )
  monthly_ingest_task_role_arn_resolved = trim(var.monthly_ingest_task_role_arn, " ") != "" ? trim(var.monthly_ingest_task_role_arn, " ") : (
    local.monthly_ingest_managed_task_definition_enabled ? aws_iam_role.monthly_ingest_task[0].arn : ""
  )
  monthly_ingest_worker_image_uri_resolved = trim(var.monthly_ingest_worker_image_uri, " ") != "" ? trim(var.monthly_ingest_worker_image_uri, " ") : (
    local.monthly_ingest_managed_task_definition_enabled ? "${aws_ecr_repository.monthly_ingest_worker[0].repository_url}:${var.monthly_ingest_worker_image_tag}" : ""
  )
  monthly_ingest_task_definition_arn_resolved = trim(var.monthly_ingest_task_definition_arn, " ") != "" ? trim(var.monthly_ingest_task_definition_arn, " ") : (
    local.monthly_ingest_managed_task_definition_enabled ? aws_ecs_task_definition.monthly_ingest_worker[0].arn : ""
  )
  monthly_ingest_task_allowed_bucket_arns = distinct(concat([aws_s3_bucket.irs_data.arn], var.monthly_ingest_task_allowed_bucket_arns))
  monthly_ingest_task_allowed_object_arns = [for arn in local.monthly_ingest_task_allowed_bucket_arns : "${arn}/*"]
}

resource "aws_ecr_repository" "monthly_ingest_worker" {
  count = local.monthly_ingest_managed_task_definition_enabled ? 1 : 0

  name                 = local.monthly_ingest_worker_repository_name
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = local.platform_common_tags
}

resource "aws_cloudwatch_log_group" "monthly_ingest_task" {
  count = local.monthly_ingest_managed_task_definition_enabled ? 1 : 0

  name              = "/aws/ecs/${local.monthly_ingest_workflow_name}"
  retention_in_days = var.monthly_ingest_task_log_retention_days
  tags              = local.platform_common_tags
}

resource "aws_iam_role" "monthly_ingest_task_execution" {
  count = local.monthly_ingest_managed_task_definition_enabled && trim(var.monthly_ingest_task_execution_role_arn, " ") == "" ? 1 : 0

  name = "${local.monthly_ingest_state_machine_role_name}-task-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "monthly_ingest_task_execution" {
  count = local.monthly_ingest_managed_task_definition_enabled && trim(var.monthly_ingest_task_execution_role_arn, " ") == "" ? 1 : 0

  role       = aws_iam_role.monthly_ingest_task_execution[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "monthly_ingest_task" {
  count = local.monthly_ingest_managed_task_definition_enabled && trim(var.monthly_ingest_task_role_arn, " ") == "" ? 1 : 0

  name = "${local.monthly_ingest_state_machine_role_name}-task"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy" "monthly_ingest_task" {
  count = local.monthly_ingest_managed_task_definition_enabled && trim(var.monthly_ingest_task_role_arn, " ") == "" ? 1 : 0

  name = "${local.monthly_ingest_state_machine_role_name}-task-policy"
  role = aws_iam_role.monthly_ingest_task[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "MonthlyIngestBucketList"
        Effect = "Allow"
        Action = ["s3:ListBucket"]
        Resource = local.monthly_ingest_task_allowed_bucket_arns
      },
      {
        Sid    = "MonthlyIngestObjectReadWrite"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = local.monthly_ingest_task_allowed_object_arns
      }
    ]
  })
}

resource "aws_ecs_task_definition" "monthly_ingest_worker" {
  count = local.monthly_ingest_managed_task_definition_enabled ? 1 : 0

  family                   = local.monthly_ingest_workflow_name
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = tostring(var.monthly_ingest_task_cpu)
  memory                   = tostring(var.monthly_ingest_task_memory)
  execution_role_arn       = local.monthly_ingest_task_execution_role_arn_resolved
  task_role_arn            = local.monthly_ingest_task_role_arn_resolved

  ephemeral_storage {
    size_in_gib = var.monthly_ingest_task_ephemeral_storage_gib
  }

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  container_definitions = jsonencode([
    {
      name      = trim(var.monthly_ingest_container_name, " ")
      image     = local.monthly_ingest_worker_image_uri_resolved
      essential = true
      command   = ["python", "monthly_ingest_worker.py"]
      environment = [
        {
          name  = "AWS_REGION"
          value = var.aws_region
        },
        {
          name  = "APP_ENV"
          value = var.environment
        },
        {
          name  = "FORM990_ZIP_MAX_XML_FILE_SIZE_BYTES"
          value = tostring(var.form990_zip_max_xml_file_size_bytes)
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.monthly_ingest_task[0].name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])

  tags = local.platform_common_tags
}
