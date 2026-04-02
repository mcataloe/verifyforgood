locals {
  worker_ecs_managed_image_enabled = var.worker_ecs_enabled && trim(var.worker_ecs_image_uri, " ") == ""
  worker_ecs_image_uri_resolved = trim(var.worker_ecs_image_uri, " ") != "" ? trim(var.worker_ecs_image_uri, " ") : (
    local.worker_ecs_managed_image_enabled ? "${aws_ecr_repository.worker[0].repository_url}:${var.worker_ecs_image_tag}" : ""
  )
  worker_ecs_secret_arns_resolved = {
    for name, arn in var.worker_ecs_secret_arns :
    trim(name, " ") => trim(arn, " ")
    if trim(name, " ") != "" && trim(arn, " ") != ""
  }
  worker_ecs_execution_secret_arns = distinct(values(local.worker_ecs_secret_arns_resolved))
  worker_ecs_container_plaintext_environment = {
    DATABASE                                         = aws_glue_catalog_database.eo_bmf.name
    TABLE                                            = aws_glue_catalog_table.eo_bmf.name
    WORKGROUP                                        = aws_athena_workgroup.eo_bmf.name
    FORM990_FILINGS_TABLE                            = aws_glue_catalog_table.form990_metadata.name
    FORM990_METRICS_TABLE                            = aws_glue_catalog_table.form990_metrics.name
    FORM990_GOVERNANCE_TABLE                         = aws_glue_catalog_table.form990_governance.name
    FORM990_QUALITY_TABLE                            = aws_glue_catalog_table.form990_quality.name
    THIRD_PARTY_INTEGRATIONS_ENABLED                 = tostring(var.third_party_integrations_enabled)
    INTEGRATION_CANDID_ENABLED                       = tostring(var.integration_candid_enabled)
    INTEGRATION_CANDID_CLIENT_ID                     = var.integration_candid_client_id
    INTEGRATION_CANDID_CLIENT_SECRET                 = var.integration_candid_client_secret
    INTEGRATION_CHARITY_NAVIGATOR_ENABLED            = tostring(var.integration_charity_navigator_enabled)
    INTEGRATION_CHARITY_NAVIGATOR_API_KEY            = var.integration_charity_navigator_api_key
    DEFAULT_REQUIRE_CANDID_FOR_EVALUATION            = tostring(var.default_require_candid_for_evaluation)
    DEFAULT_REQUIRE_CHARITY_NAVIGATOR_FOR_EVALUATION = tostring(var.default_require_charity_navigator_for_evaluation)
    ENRICHMENT_MOCK_OFFERED                          = tostring(var.enrichment_mock_offered != null ? var.enrichment_mock_offered : var.enrichment_mock_enabled)
    ENRICHMENT_MOCK_ENABLED                          = tostring(var.enrichment_mock_enabled)
    ENRICHMENT_CANDID_OFFERED                        = tostring(var.enrichment_candid_offered != null ? var.enrichment_candid_offered : var.enrichment_candid_enabled)
    ENRICHMENT_CANDID_ENABLED                        = tostring(var.enrichment_candid_enabled)
    ENRICHMENT_CANDID_ENDPOINT                       = var.enrichment_candid_endpoint
    ENRICHMENT_CANDID_API_KEY                        = var.enrichment_candid_api_key
    ENRICHMENT_TIMEOUT_SECONDS                       = tostring(var.enrichment_timeout_seconds)
    ENRICHMENT_STATE_REGISTRY_OFFERED                = tostring(var.enrichment_state_registry_offered != null ? var.enrichment_state_registry_offered : (var.enrichment_state_registry_enabled || var.enrichment_state_registry_mock_enabled))
    ENRICHMENT_STATE_REGISTRY_ENABLED                = tostring(var.enrichment_state_registry_enabled)
    ENRICHMENT_STATE_REGISTRY_MOCK_ENABLED           = tostring(var.enrichment_state_registry_mock_enabled)
    ENRICHMENT_STATE_REGISTRY_ENDPOINT               = var.enrichment_state_registry_endpoint
    ENRICHMENT_STATE_REGISTRY_COLORADO_ENABLED       = tostring(var.enrichment_state_registry_colorado_enabled)
    ENRICHMENT_STATE_REGISTRY_COLORADO_APP_TOKEN     = var.enrichment_state_registry_colorado_app_token
    ENRICHMENT_STATE_REGISTRY_KENTUCKY_ENABLED       = tostring(var.enrichment_state_registry_kentucky_enabled)
    ENRICHMENT_STATE_REGISTRY_KENTUCKY_COMPANIES_URL = var.enrichment_state_registry_kentucky_companies_url
    ENRICHMENT_STATE_BUSINESS_OFFERED                = tostring(var.enrichment_state_business_offered != null ? var.enrichment_state_business_offered : (var.enrichment_state_business_enabled || var.enrichment_state_business_mock_enabled))
    ENRICHMENT_STATE_BUSINESS_ENABLED                = tostring(var.enrichment_state_business_enabled)
    ENRICHMENT_STATE_BUSINESS_MOCK_ENABLED           = tostring(var.enrichment_state_business_mock_enabled)
    ENRICHMENT_STATE_BUSINESS_ENDPOINT               = var.enrichment_state_business_endpoint
    ENRICHMENT_USASPENDING_OFFERED                   = tostring(var.enrichment_usaspending_offered != null ? var.enrichment_usaspending_offered : (var.enrichment_usaspending_enabled || var.enrichment_usaspending_mock_enabled))
    ENRICHMENT_USASPENDING_ENABLED                   = tostring(var.enrichment_usaspending_enabled)
    ENRICHMENT_USASPENDING_MOCK_ENABLED              = tostring(var.enrichment_usaspending_mock_enabled)
    ENRICHMENT_USASPENDING_ENDPOINT                  = var.enrichment_usaspending_endpoint
    ENRICHMENT_OFAC_OFFERED                          = tostring(var.enrichment_ofac_offered != null ? var.enrichment_ofac_offered : (var.enrichment_ofac_enabled || var.enrichment_ofac_mock_enabled))
    ENRICHMENT_OFAC_ENABLED                          = tostring(var.enrichment_ofac_enabled)
    ENRICHMENT_OFAC_MOCK_ENABLED                     = tostring(var.enrichment_ofac_mock_enabled)
    ENRICHMENT_OFAC_ENDPOINT                         = var.enrichment_ofac_endpoint
    APP_NAME                                         = var.app_name
    PUBLIC_BRAND_NAME                                = var.public_brand_name
    SUPPORT_EMAIL                                    = var.support_email
    DOMAIN                                           = var.domain
    PROFILE_TABLE_NAME                               = aws_dynamodb_table.profiles.name
    APP_ENV                                          = var.environment
    REFRESH_MODE                                     = var.refresh_mode
    REFRESH_BATCH_SIZE                               = tostring(var.refresh_batch_size)
    FORCE_REFRESH                                    = tostring(var.refresh_force)
    REFRESH_SOURCE_DETECTION_ENABLED                 = tostring(var.refresh_source_detection_enabled)
    BOOTSTRAP_NONPROD_OVERRIDE                       = tostring(var.bootstrap_nonprod_override)
    BOOTSTRAP_START_AFTER_EIN                        = var.bootstrap_start_after_ein
    BOOTSTRAP_MAX_BATCHES_PER_RUN                    = tostring(var.bootstrap_max_batches_per_run)
    OPS_METADATA_BUCKET                              = aws_s3_bucket.irs_data.bucket
    OPS_METADATA_PREFIX                              = var.ops_metadata_prefix
  }
  worker_ecs_container_environment = {
    for name, value in local.worker_ecs_container_plaintext_environment :
    name => value if !contains(keys(local.worker_ecs_secret_arns_resolved), name)
  }

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

resource "aws_ecr_repository" "worker" {
  count = local.worker_ecs_managed_image_enabled ? 1 : 0

  name                 = local.worker_ecr_repository_name
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = local.platform_common_tags
}

resource "aws_cloudwatch_log_group" "worker_task" {
  count = var.worker_ecs_enabled ? 1 : 0

  name              = "/aws/ecs/${local.worker_ecs_service_name}"
  retention_in_days = var.worker_ecs_log_retention_days
  tags              = local.platform_common_tags
}

resource "aws_security_group" "worker_task" {
  count = var.worker_ecs_enabled ? 1 : 0

  name        = local.worker_task_security_group_name
  description = "Security group for the ECS worker tasks."
  vpc_id      = var.worker_ecs_vpc_id

  egress {
    description = "Allow outbound traffic from the ECS worker tasks."
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = local.platform_common_tags
}

resource "aws_iam_role" "worker_task_execution" {
  count = var.worker_ecs_enabled ? 1 : 0

  name = local.worker_task_execution_role_name

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [ {
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    } ]
  })
}

resource "aws_iam_role_policy_attachment" "worker_task_execution" {
  count = var.worker_ecs_enabled ? 1 : 0

  role       = aws_iam_role.worker_task_execution[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "worker_task_execution_secrets" {
  count = var.worker_ecs_enabled && (length(local.worker_ecs_execution_secret_arns) > 0 || length(var.worker_ecs_secret_kms_key_arns) > 0) ? 1 : 0

  name = "${local.worker_task_execution_role_name}-secrets"
  role = aws_iam_role.worker_task_execution[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat(
      length(local.worker_ecs_execution_secret_arns) > 0 ? [
        {
          Sid    = "WorkerTaskExecutionSecretRead"
          Effect = "Allow"
          Action = [
            "secretsmanager:GetSecretValue",
            "secretsmanager:DescribeSecret",
            "ssm:GetParameters",
            "ssm:GetParameter"
          ]
          Resource = local.worker_ecs_execution_secret_arns
        }
      ] : [],
      length(var.worker_ecs_secret_kms_key_arns) > 0 ? [
        {
          Sid    = "WorkerTaskExecutionSecretDecrypt"
          Effect = "Allow"
          Action = ["kms:Decrypt"]
          Resource = var.worker_ecs_secret_kms_key_arns
        }
      ] : [],
    )
  })
}

resource "aws_iam_role" "worker_task" {
  count = var.worker_ecs_enabled ? 1 : 0

  name = local.worker_task_role_name

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [ {
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    } ]
  })
}

resource "aws_iam_role_policy" "worker_task" {
  count = var.worker_ecs_enabled ? 1 : 0

  name = "${local.worker_task_role_name}-policy"
  role = aws_iam_role.worker_task[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "WorkerTaskDataPlane"
        Effect = "Allow"
        Action = [
          "s3:*",
          "athena:*",
          "glue:*"
        ]
        Resource = "*"
      },
      {
        Sid    = "WorkerTaskProfileStore"
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:Query",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem"
        ]
        Resource = [
          aws_dynamodb_table.profiles.arn
        ]
      }
    ]
  })
}

resource "aws_ecs_task_definition" "worker" {
  count = var.worker_ecs_enabled ? 1 : 0

  family                   = local.worker_task_definition_family
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = tostring(var.worker_ecs_task_cpu)
  memory                   = tostring(var.worker_ecs_task_memory)
  execution_role_arn       = aws_iam_role.worker_task_execution[0].arn
  task_role_arn            = aws_iam_role.worker_task[0].arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  container_definitions = jsonencode([
    {
      name      = trim(var.worker_ecs_container_name, " ")
      image     = local.worker_ecs_image_uri_resolved
      essential = true
      environment = [
        for name in sort(keys(local.worker_ecs_container_environment)) : {
          name  = name
          value = tostring(local.worker_ecs_container_environment[name])
        }
      ]
      secrets = [
        for name in sort(keys(local.worker_ecs_secret_arns_resolved)) : {
          name      = name
          valueFrom = local.worker_ecs_secret_arns_resolved[name]
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.worker_task[0].name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])

  tags = local.platform_common_tags
}

resource "aws_ecs_service" "worker" {
  count = var.worker_ecs_enabled ? 1 : 0

  name                   = local.worker_ecs_service_name
  cluster                = aws_ecs_cluster.api[0].id
  task_definition        = aws_ecs_task_definition.worker[0].arn
  desired_count          = var.worker_ecs_desired_count
  launch_type            = "FARGATE"
  enable_execute_command = true

  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 100

  network_configuration {
    subnets          = var.worker_ecs_private_subnet_ids
    security_groups  = concat([aws_security_group.worker_task[0].id], var.worker_ecs_additional_security_group_ids)
    assign_public_ip = false
  }

  tags = local.platform_common_tags
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
        Sid      = "MonthlyIngestBucketList"
        Effect   = "Allow"
        Action   = ["s3:ListBucket"]
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
      entryPoint = ["python", "-m", "charity_status_backend.ingest_task.cli"]
      command    = ["monthly-worker"]
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
