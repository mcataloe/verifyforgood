locals {
  worker_ecs_managed_image_enabled = trim(var.worker_ecs_image_uri, " ") == ""
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
    APP_ENV                                          = var.environment
    BOOTSTRAP_NONPROD_OVERRIDE                       = tostring(var.bootstrap_nonprod_override)
    BOOTSTRAP_START_AFTER_EIN                        = var.bootstrap_start_after_ein
    BOOTSTRAP_MAX_BATCHES_PER_RUN                    = tostring(var.bootstrap_max_batches_per_run)
    PLATFORM_NONPROFIT_STORE_BACKEND                 = var.platform_nonprofit_store_backend
    PLATFORM_NONPROFIT_POSTGRES_ENABLED              = tostring(var.platform_nonprofit_postgres_enabled)
    PLATFORM_NONPROFIT_POSTGRES_SECRET_ARN           = var.platform_nonprofit_postgres_enabled ? trim(var.platform_nonprofit_postgres_secret_arn, " ") : ""
    PLATFORM_NONPROFIT_POSTGRES_HOST                 = var.platform_nonprofit_postgres_enabled ? trim(var.platform_nonprofit_postgres_host, " ") : ""
    PLATFORM_NONPROFIT_POSTGRES_PORT                 = var.platform_nonprofit_postgres_enabled ? tostring(var.platform_nonprofit_postgres_port) : ""
    PLATFORM_NONPROFIT_POSTGRES_DATABASE             = var.platform_nonprofit_postgres_enabled ? trim(var.platform_nonprofit_postgres_database_name, " ") : ""
    PLATFORM_NONPROFIT_POSTGRES_SSLMODE              = var.platform_nonprofit_postgres_enabled ? trim(var.platform_nonprofit_postgres_sslmode, " ") : ""
  }
  worker_ecs_container_environment = {
    for name, value in local.worker_ecs_container_plaintext_environment :
    name => value if !contains(keys(local.worker_ecs_secret_arns_resolved), name)
  }

  monthly_ingest_managed_image_enabled = trim(var.monthly_ingest_worker_image_uri, " ") == ""
  monthly_ingest_managed_task_definition_enabled = trim(var.monthly_ingest_task_definition_arn, " ") == ""
  monthly_ingest_task_execution_role_arn_resolved = trim(var.monthly_ingest_task_execution_role_arn, " ") != "" ? trim(var.monthly_ingest_task_execution_role_arn, " ") : (
    local.monthly_ingest_managed_task_definition_enabled ? aws_iam_role.monthly_ingest_task_execution[0].arn : ""
  )
  monthly_ingest_task_role_arn_resolved = trim(var.monthly_ingest_task_role_arn, " ") != "" ? trim(var.monthly_ingest_task_role_arn, " ") : (
    local.monthly_ingest_managed_task_definition_enabled ? aws_iam_role.monthly_ingest_task[0].arn : ""
  )
  monthly_ingest_worker_image_uri_resolved = trim(var.monthly_ingest_worker_image_uri, " ") != "" ? trim(var.monthly_ingest_worker_image_uri, " ") : (
    local.monthly_ingest_managed_image_enabled ? "${aws_ecr_repository.monthly_ingest_worker[0].repository_url}:${var.monthly_ingest_worker_image_tag}" : ""
  )
  monthly_ingest_task_definition_arn_resolved = trim(var.monthly_ingest_task_definition_arn, " ") != "" ? trim(var.monthly_ingest_task_definition_arn, " ") : (
    local.monthly_ingest_managed_task_definition_enabled ? aws_ecs_task_definition.monthly_ingest_worker[0].arn : ""
  )
  monthly_ingest_cluster_arn_resolved = trim(var.monthly_ingest_ecs_cluster_arn, " ") != "" ? trim(var.monthly_ingest_ecs_cluster_arn, " ") : (
    (var.api_ecs_enabled || var.worker_ecs_enabled) ? aws_ecs_cluster.api[0].arn : ""
  )
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
    Statement = concat(
      [],
      var.platform_nonprofit_postgres_enabled ? [
        {
          Sid    = "WorkerTaskNonprofitPostgresSecretRead"
          Effect = "Allow"
          Action = [
            "secretsmanager:GetSecretValue",
            "secretsmanager:DescribeSecret"
          ]
          Resource = [
            trim(var.platform_nonprofit_postgres_secret_arn, " ")
          ]
        }
      ] : [],
      var.platform_nonprofit_postgres_enabled && trim(var.platform_nonprofit_postgres_secret_kms_key_arn, " ") != "" ? [
        {
          Sid    = "WorkerTaskNonprofitPostgresSecretDecrypt"
          Effect = "Allow"
          Action = [
            "kms:Decrypt"
          ]
          Resource = [
            trim(var.platform_nonprofit_postgres_secret_kms_key_arn, " ")
          ]
        }
      ] : [],
    )
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
  count = local.monthly_ingest_managed_image_enabled ? 1 : 0

  name                 = local.monthly_ingest_worker_repository_name
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = local.platform_common_tags
}

resource "aws_cloudwatch_log_group" "monthly_ingest_task" {
  count = local.monthly_ingest_managed_task_definition_enabled ? 1 : 0

  name              = "/aws/ecs/${local.monthly_ingest_state_machine_name}"
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
    Statement = concat(
      [],
      var.platform_nonprofit_postgres_enabled ? [
        {
          Sid    = "MonthlyIngestNonprofitPostgresSecretRead"
          Effect = "Allow"
          Action = [
            "secretsmanager:GetSecretValue",
            "secretsmanager:DescribeSecret"
          ]
          Resource = [
            trim(var.platform_nonprofit_postgres_secret_arn, " ")
          ]
        }
      ] : [],
      var.platform_nonprofit_postgres_enabled && trim(var.platform_nonprofit_postgres_secret_kms_key_arn, " ") != "" ? [
        {
          Sid    = "MonthlyIngestNonprofitPostgresSecretDecrypt"
          Effect = "Allow"
          Action = [
            "kms:Decrypt"
          ]
          Resource = [
            trim(var.platform_nonprofit_postgres_secret_kms_key_arn, " ")
          ]
        }
      ] : [],
    )
  })
}

resource "aws_ecs_task_definition" "monthly_ingest_worker" {
  count = local.monthly_ingest_managed_task_definition_enabled ? 1 : 0

  family                   = local.monthly_ingest_state_machine_name
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
      entryPoint = ["python", "-m", "verification_backend.ingest_task.cli"]
      command    = ["ecs-run"]
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
          name  = "PLATFORM_NONPROFIT_STORE_BACKEND"
          value = var.platform_nonprofit_store_backend
        },
        {
          name  = "PLATFORM_NONPROFIT_POSTGRES_ENABLED"
          value = tostring(var.platform_nonprofit_postgres_enabled)
        },
        {
          name  = "PLATFORM_NONPROFIT_POSTGRES_SECRET_ARN"
          value = var.platform_nonprofit_postgres_enabled ? trim(var.platform_nonprofit_postgres_secret_arn, " ") : ""
        },
        {
          name  = "PLATFORM_NONPROFIT_POSTGRES_HOST"
          value = var.platform_nonprofit_postgres_enabled ? trim(var.platform_nonprofit_postgres_host, " ") : ""
        },
        {
          name  = "PLATFORM_NONPROFIT_POSTGRES_PORT"
          value = var.platform_nonprofit_postgres_enabled ? tostring(var.platform_nonprofit_postgres_port) : ""
        },
        {
          name  = "PLATFORM_NONPROFIT_POSTGRES_DATABASE"
          value = var.platform_nonprofit_postgres_enabled ? trim(var.platform_nonprofit_postgres_database_name, " ") : ""
        },
        {
          name  = "PLATFORM_NONPROFIT_POSTGRES_SSLMODE"
          value = var.platform_nonprofit_postgres_enabled ? trim(var.platform_nonprofit_postgres_sslmode, " ") : ""
        },
        {
          name  = "FORM990_ZIP_MAX_XML_FILE_SIZE_BYTES"
          value = tostring(var.form990_zip_max_xml_file_size_bytes)
        },
        {
          name  = "WORKSPACE_PATH"
          value = "/tmp/charity-status/form990"
        },
        {
          name  = "STRICT_MODE"
          value = "false"
        },
        {
          name  = "MAX_ARCHIVES"
          value = ""
        },
        {
          name  = "LOG_LEVEL"
          value = "INFO"
        },
        {
          name  = "FORM990_EXECUTION_MODE"
          value = "scheduled"
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

resource "aws_ecs_task_definition" "eo_bmf_ingest_worker" {
  count = trim(local.monthly_ingest_worker_image_uri_resolved, " ") != "" ? 1 : 0

  family                   = "${local.monthly_ingest_state_machine_name}-eo-bmf"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = tostring(var.monthly_ingest_task_cpu)
  memory                   = tostring(var.monthly_ingest_task_memory)
  execution_role_arn       = local.monthly_ingest_task_execution_role_arn_resolved
  task_role_arn            = local.monthly_ingest_task_role_arn_resolved

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  container_definitions = jsonencode([
    {
      name       = trim(var.monthly_ingest_container_name, " ")
      image      = local.monthly_ingest_worker_image_uri_resolved
      essential  = true
      entryPoint = ["python", "-m", "verification_backend.ingest_task.cli"]
      command    = ["ecs-run-eo-bmf"]
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
          name  = "PLATFORM_NONPROFIT_STORE_BACKEND"
          value = var.platform_nonprofit_store_backend
        },
        {
          name  = "PLATFORM_NONPROFIT_POSTGRES_ENABLED"
          value = tostring(var.platform_nonprofit_postgres_enabled)
        },
        {
          name  = "PLATFORM_NONPROFIT_POSTGRES_SECRET_ARN"
          value = var.platform_nonprofit_postgres_enabled ? trim(var.platform_nonprofit_postgres_secret_arn, " ") : ""
        },
        {
          name  = "PLATFORM_NONPROFIT_POSTGRES_HOST"
          value = var.platform_nonprofit_postgres_enabled ? trim(var.platform_nonprofit_postgres_host, " ") : ""
        },
        {
          name  = "PLATFORM_NONPROFIT_POSTGRES_PORT"
          value = var.platform_nonprofit_postgres_enabled ? tostring(var.platform_nonprofit_postgres_port) : ""
        },
        {
          name  = "PLATFORM_NONPROFIT_POSTGRES_DATABASE"
          value = var.platform_nonprofit_postgres_enabled ? trim(var.platform_nonprofit_postgres_database_name, " ") : ""
        },
        {
          name  = "PLATFORM_NONPROFIT_POSTGRES_SSLMODE"
          value = var.platform_nonprofit_postgres_enabled ? trim(var.platform_nonprofit_postgres_sslmode, " ") : ""
        },
        {
          name  = "WORKSPACE_PATH"
          value = "/tmp/charity-status/eo-bmf"
        },
        {
          name  = "STRICT_MODE"
          value = "false"
        },
        {
          name  = "LOG_LEVEL"
          value = "INFO"
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

resource "aws_iam_role" "ingest_schedule" {
  count = 1

  name = "${local.monthly_ingest_state_machine_role_name}-events"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "events.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy" "ingest_schedule" {
  count = 1

  name = "${local.monthly_ingest_state_machine_role_name}-events-policy"
  role = aws_iam_role.ingest_schedule[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "RunScheduledIngestTasks"
        Effect = "Allow"
        Action = ["ecs:RunTask"]
        Resource = compact([
          local.monthly_ingest_task_definition_arn_resolved,
          trim(local.monthly_ingest_worker_image_uri_resolved, " ") != "" ? aws_ecs_task_definition.eo_bmf_ingest_worker[0].arn : "",
        ])
      },
      {
        Sid    = "PassScheduledIngestTaskRoles"
        Effect = "Allow"
        Action = ["iam:PassRole"]
        Resource = compact([
          trim(local.monthly_ingest_task_execution_role_arn_resolved, " "),
          trim(local.monthly_ingest_task_role_arn_resolved, " "),
        ])
      },
    ]
  })
}

resource "aws_cloudwatch_event_rule" "daily_ingest" {
  name                = local.scheduled_workflow_names.regulatory_data_ingestion
  schedule_expression = "cron(0 3 * * ? *)"
}

resource "aws_cloudwatch_event_target" "daily_ingest_ecs_target" {
  count = trim(local.monthly_ingest_cluster_arn_resolved, " ") != "" && trim(local.monthly_ingest_worker_image_uri_resolved, " ") != "" ? 1 : 0

  rule      = aws_cloudwatch_event_rule.daily_ingest.name
  target_id = "eo-bmf-ecs-ingest"
  arn       = local.monthly_ingest_cluster_arn_resolved
  role_arn  = aws_iam_role.ingest_schedule[0].arn

  ecs_target {
    launch_type         = "FARGATE"
    task_count          = 1
    task_definition_arn = aws_ecs_task_definition.eo_bmf_ingest_worker[0].arn

    network_configuration {
      subnets          = var.monthly_ingest_private_subnet_ids
      security_groups  = var.monthly_ingest_task_security_group_ids
      assign_public_ip = false
    }
  }
}

resource "aws_cloudwatch_event_rule" "form990_schedule" {
  count = trim(var.form990_schedule_expression, " ") != "" ? 1 : 0

  name                = local.scheduled_workflow_names.monthly_filing_ingestion
  schedule_expression = var.form990_schedule_expression
}

resource "aws_cloudwatch_event_target" "form990_ecs_target" {
  count = trim(var.form990_schedule_expression, " ") != "" && trim(local.monthly_ingest_cluster_arn_resolved, " ") != "" && trim(local.monthly_ingest_task_definition_arn_resolved, " ") != "" ? 1 : 0

  rule      = aws_cloudwatch_event_rule.form990_schedule[0].name
  target_id = "form990-ecs-ingest"
  arn       = local.monthly_ingest_cluster_arn_resolved
  role_arn  = aws_iam_role.ingest_schedule[0].arn

  ecs_target {
    launch_type         = "FARGATE"
    task_count          = 1
    task_definition_arn = local.monthly_ingest_task_definition_arn_resolved

    network_configuration {
      subnets          = var.monthly_ingest_private_subnet_ids
      security_groups  = var.monthly_ingest_task_security_group_ids
      assign_public_ip = false
    }
  }
}

