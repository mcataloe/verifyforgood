locals {
  api_ecs_managed_image_enabled = var.api_ecs_enabled && trim(var.api_ecs_image_uri, " ") == ""
  api_ecs_image_uri_resolved = trim(var.api_ecs_image_uri, " ") != "" ? trim(var.api_ecs_image_uri, " ") : (
    local.api_ecs_managed_image_enabled ? "${aws_ecr_repository.api[0].repository_url}:${var.api_ecs_image_tag}" : ""
  )
  api_alb_certificate_arn_resolved = trim(var.api_alb_certificate_arn, " ") != "" ? trim(var.api_alb_certificate_arn, " ") : (
    local.enable_custom_domain ? aws_acm_certificate_validation.cert[0].certificate_arn : ""
  )
  api_ecs_secret_arns_resolved = {
    for name, arn in var.api_ecs_secret_arns :
    trim(name, " ") => trim(arn, " ")
    if trim(name, " ") != "" && trim(arn, " ") != ""
  }
  api_ecs_execution_secret_arns = distinct(values(local.api_ecs_secret_arns_resolved))
  api_ecs_container_plaintext_environment = {
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
    PROFILE_TABLE_NAME                               = aws_dynamodb_table.profiles.name
    IDENTITY_TABLE_NAME                              = aws_dynamodb_table.identity.name
    CONTROL_PLANE_TABLE_NAME                         = aws_dynamodb_table.control_plane.name
    APP_ENV                                          = var.environment
    CORS_ALLOWED_ORIGINS                             = join(",", var.cors_allowed_origins)
    SERVING_DDB_ENABLED                              = tostring(var.serving_dynamodb_enabled)
    BATCH_VERIFY_MAX_SIZE                            = tostring(var.batch_verify_max_size)
    SEARCH_MAX_LIMIT                                 = tostring(var.search_max_limit)
    SEARCH_DEFAULT_LIMIT                             = tostring(var.search_default_limit)
    API_AUTH_ENABLED                                 = tostring(var.api_auth_enabled)
    API_KEY_RECORDS_JSON                             = var.api_key_records_json
    OAUTH_M2M_ENABLED                                = tostring(var.oauth_m2m_enabled)
    OAUTH_TOKEN_RECORDS_JSON                         = var.oauth_token_records_json
    OAUTH_CLIENT_RECORDS_JSON                        = var.oauth_client_records_json
    OAUTH_TOKEN_TTL_SECONDS                          = tostring(var.oauth_token_ttl_seconds)
    ADMIN_KEY_RECORDS_JSON                           = var.admin_key_records_json
    APP_NAME                                         = var.app_name
    PUBLIC_BRAND_NAME                                = var.public_brand_name
    SUPPORT_EMAIL                                    = var.support_email
    DOMAIN                                           = var.domain
    ORGANIZATION_INTEGRATION_SETTINGS_JSON           = var.organization_integration_settings_json
    TENANT_INTEGRATION_SETTINGS_JSON                 = var.tenant_integration_settings_json
    STRIPE_BILLING_ENABLED                           = tostring(var.stripe_billing_enabled)
    STRIPE_PRICE_IDS                                 = var.stripe_price_ids_json
    STRIPE_SECRET_KEY                                = var.stripe_secret_key
    STRIPE_WEBHOOK_SECRET                            = var.stripe_webhook_secret
    FREE_TRIAL_ENABLED                               = tostring(var.free_trial_enabled)
    FREE_TRIAL_DURATION_DAYS                         = tostring(var.free_trial_duration_days)
    FREE_TRIAL_PLAN_CODE                             = var.free_trial_plan_code
    FREE_TRIAL_MONTHLY_REQUEST_LIMIT                 = var.free_trial_monthly_request_limit != null ? tostring(var.free_trial_monthly_request_limit) : ""
    PLATFORM_POSTGRES_ENABLED                        = tostring(var.platform_postgres_enabled)
    PLATFORM_POSTGRES_SECRET_ARN                     = local.platform_postgres_secret_arn_resolved
    PLATFORM_POSTGRES_HOST                           = var.platform_postgres_enabled ? aws_db_instance.platform_postgres[0].address : ""
    PLATFORM_POSTGRES_PORT                           = tostring(var.platform_postgres_port)
    PLATFORM_POSTGRES_DATABASE                       = var.platform_postgres_database_name
    PLATFORM_POSTGRES_SSLMODE                        = var.platform_postgres_sslmode
    PLATFORM_IDENTITY_STORE_BACKEND                  = var.platform_identity_store_backend
    PLATFORM_ORGANIZATION_SETTINGS_STORE_BACKEND     = var.platform_organization_settings_store_backend
    PLATFORM_CONTROL_PLANE_STORE_BACKEND             = var.platform_control_plane_store_backend
    PLATFORM_NONPROFIT_QUERY_BACKEND                 = var.platform_nonprofit_query_backend
    ORGANIZATION_SETTINGS_TABLE_NAME                 = aws_dynamodb_table.organization_settings.name
    OPS_METADATA_BUCKET                              = aws_s3_bucket.irs_data.bucket
    OPS_METADATA_PREFIX                              = var.ops_metadata_prefix
    FORM990_ORCHESTRATOR_FUNCTION_NAME               = aws_lambda_function.form990_orchestrator.function_name
  }
  api_ecs_container_environment = {
    for name, value in local.api_ecs_container_plaintext_environment :
    name => value if !contains(keys(local.api_ecs_secret_arns_resolved), name)
  }
}

resource "aws_ecs_cluster" "api" {
  count = var.api_ecs_enabled ? 1 : 0

  name = local.ecs_cluster_name

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = local.platform_common_tags
}

resource "aws_ecr_repository" "api" {
  count = var.api_ecs_enabled ? 1 : 0

  name                 = local.api_ecr_repository_name
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = local.platform_common_tags
}

resource "aws_cloudwatch_log_group" "api_task" {
  count = var.api_ecs_enabled ? 1 : 0

  name              = "/aws/ecs/${local.api_ecs_service_name}"
  retention_in_days = var.api_ecs_log_retention_days
  tags              = local.platform_common_tags
}

resource "aws_security_group" "api_alb" {
  count = var.api_ecs_enabled ? 1 : 0

  name        = local.api_alb_security_group_name
  description = "Security group for the ECS API application load balancer."
  vpc_id      = var.api_ecs_vpc_id

  ingress {
    description = "Allow HTTP ingress to the API ALB."
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Allow HTTPS ingress to the API ALB."
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow outbound traffic from the API ALB."
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = local.platform_common_tags
}

resource "aws_security_group" "api_task" {
  count = var.api_ecs_enabled ? 1 : 0

  name        = local.api_task_security_group_name
  description = "Security group for the ECS API tasks."
  vpc_id      = var.api_ecs_vpc_id

  ingress {
    description     = "Allow application traffic from the API ALB."
    from_port       = var.api_ecs_container_port
    to_port         = var.api_ecs_container_port
    protocol        = "tcp"
    security_groups = [aws_security_group.api_alb[0].id]
  }

  egress {
    description = "Allow outbound traffic from the ECS API tasks."
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = local.platform_common_tags
}

resource "aws_lb" "api" {
  count = var.api_ecs_enabled ? 1 : 0

  name               = local.api_alb_name
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.api_alb[0].id]
  subnets            = var.api_ecs_public_subnet_ids

  tags = local.platform_common_tags
}

resource "aws_lb_target_group" "api" {
  count = var.api_ecs_enabled ? 1 : 0

  name                 = local.api_target_group_name
  port                 = var.api_ecs_container_port
  protocol             = "HTTP"
  target_type          = "ip"
  vpc_id               = var.api_ecs_vpc_id
  deregistration_delay = var.api_ecs_target_group_deregistration_delay_seconds

  health_check {
    enabled             = true
    path                = var.api_ecs_health_check_path
    matcher             = var.api_ecs_health_check_matcher
    interval            = var.api_ecs_health_check_interval_seconds
    timeout             = var.api_ecs_health_check_timeout_seconds
    healthy_threshold   = var.api_ecs_healthy_threshold
    unhealthy_threshold = var.api_ecs_unhealthy_threshold
  }

  tags = local.platform_common_tags
}

resource "aws_lb_listener" "api_http" {
  count = var.api_ecs_enabled ? 1 : 0

  load_balancer_arn = aws_lb.api[0].arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"

    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }

  lifecycle {
    precondition {
      condition     = trim(local.api_alb_certificate_arn_resolved, " ") != ""
      error_message = "api_alb_certificate_arn must be set or enable_custom_domain must provide a managed ACM certificate when api_ecs_enabled=true."
    }
  }
}

resource "aws_lb_listener" "api_https" {
  count = var.api_ecs_enabled ? 1 : 0

  load_balancer_arn = aws_lb.api[0].arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = var.api_alb_ssl_policy
  certificate_arn   = local.api_alb_certificate_arn_resolved

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api[0].arn
  }

  lifecycle {
    precondition {
      condition     = trim(local.api_alb_certificate_arn_resolved, " ") != ""
      error_message = "api_alb_certificate_arn must be set or enable_custom_domain must provide a managed ACM certificate when api_ecs_enabled=true."
    }
  }
}

resource "aws_iam_role" "api_task_execution" {
  count = var.api_ecs_enabled ? 1 : 0

  name = local.api_task_execution_role_name

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

resource "aws_iam_role_policy_attachment" "api_task_execution" {
  count = var.api_ecs_enabled ? 1 : 0

  role       = aws_iam_role.api_task_execution[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "api_task_execution_secrets" {
  count = var.api_ecs_enabled && (length(local.api_ecs_execution_secret_arns) > 0 || length(var.api_ecs_secret_kms_key_arns) > 0) ? 1 : 0

  name = "${local.api_task_execution_role_name}-secrets"
  role = aws_iam_role.api_task_execution[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat(
      length(local.api_ecs_execution_secret_arns) > 0 ? [
        {
          Sid    = "ApiTaskExecutionSecretRead"
          Effect = "Allow"
          Action = [
            "secretsmanager:GetSecretValue",
            "secretsmanager:DescribeSecret",
            "ssm:GetParameters",
            "ssm:GetParameter"
          ]
          Resource = local.api_ecs_execution_secret_arns
        }
      ] : [],
      length(var.api_ecs_secret_kms_key_arns) > 0 ? [
        {
          Sid    = "ApiTaskExecutionSecretDecrypt"
          Effect = "Allow"
          Action = [
            "kms:Decrypt"
          ]
          Resource = var.api_ecs_secret_kms_key_arns
        }
      ] : [],
    )
  })
}

resource "aws_iam_role" "api_task" {
  count = var.api_ecs_enabled ? 1 : 0

  name = local.api_task_role_name

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

resource "aws_iam_role_policy" "api_task" {
  count = var.api_ecs_enabled ? 1 : 0

  name = "${local.api_task_role_name}-policy"
  role = aws_iam_role.api_task[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat(
      [
        {
          Sid    = "ApiTaskDataPlane"
          Effect = "Allow"
          Action = [
            "s3:*",
            "athena:*",
            "glue:*"
          ]
          Resource = "*"
        },
        {
          Sid    = "ApiTaskInvokeForm990Orchestrator"
          Effect = "Allow"
          Action = [
            "lambda:InvokeFunction"
          ]
          Resource = [
            aws_lambda_function.form990_orchestrator.arn
          ]
        },
        {
          Sid    = "ApiTaskIdentityStores"
          Effect = "Allow"
          Action = [
            "dynamodb:GetItem",
            "dynamodb:Query",
            "dynamodb:PutItem",
            "dynamodb:UpdateItem",
            "dynamodb:DeleteItem"
          ]
          Resource = [
            aws_dynamodb_table.profiles.arn,
            aws_dynamodb_table.identity.arn,
            aws_dynamodb_table.organization_settings.arn,
            aws_dynamodb_table.control_plane.arn,
            "${aws_dynamodb_table.identity.arn}/index/email_lookup",
            "${aws_dynamodb_table.identity.arn}/index/user_memberships",
            "${aws_dynamodb_table.identity.arn}/index/invitation_token_lookup",
            "${aws_dynamodb_table.identity.arn}/index/organization_slug_lookup",
            "${aws_dynamodb_table.identity.arn}/index/api_key_lookup",
            "${aws_dynamodb_table.organization_settings.arn}/index/account_lookup",
            "${aws_dynamodb_table.control_plane.arn}/index/credential_lookup",
            "${aws_dynamodb_table.control_plane.arn}/index/entity_listing",
          ]
        }
      ],
      var.platform_postgres_enabled ? [
        {
          Sid    = "ApiTaskPostgresSecretRead"
          Effect = "Allow"
          Action = [
            "secretsmanager:GetSecretValue",
            "secretsmanager:DescribeSecret"
          ]
          Resource = [
            local.platform_postgres_secret_arn_resolved
          ]
        }
      ] : [],
      var.platform_postgres_enabled && trim(var.platform_postgres_secret_kms_key_arn, " ") != "" ? [
        {
          Sid    = "ApiTaskPostgresSecretDecrypt"
          Effect = "Allow"
          Action = [
            "kms:Decrypt"
          ]
          Resource = [
            trim(var.platform_postgres_secret_kms_key_arn, " ")
          ]
        }
      ] : [],
    )
  })
}

resource "aws_ecs_task_definition" "api" {
  count = var.api_ecs_enabled ? 1 : 0

  family                   = local.api_task_definition_family
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = tostring(var.api_ecs_task_cpu)
  memory                   = tostring(var.api_ecs_task_memory)
  execution_role_arn       = aws_iam_role.api_task_execution[0].arn
  task_role_arn            = aws_iam_role.api_task[0].arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  container_definitions = jsonencode([
    {
      name      = trim(var.api_ecs_container_name, " ")
      image     = local.api_ecs_image_uri_resolved
      essential = true
      portMappings = [
        {
          containerPort = var.api_ecs_container_port
          hostPort      = var.api_ecs_container_port
          protocol      = "tcp"
        }
      ]
      environment = [
        for name in sort(keys(local.api_ecs_container_environment)) : {
          name  = name
          value = tostring(local.api_ecs_container_environment[name])
        }
      ]
      secrets = [
        for name in sort(keys(local.api_ecs_secret_arns_resolved)) : {
          name      = name
          valueFrom = local.api_ecs_secret_arns_resolved[name]
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.api_task[0].name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])

  tags = local.platform_common_tags
}

resource "aws_ecs_service" "api" {
  count = var.api_ecs_enabled ? 1 : 0

  name                              = local.api_ecs_service_name
  cluster                           = aws_ecs_cluster.api[0].id
  task_definition                   = aws_ecs_task_definition.api[0].arn
  desired_count                     = var.api_ecs_desired_count
  launch_type                       = "FARGATE"
  health_check_grace_period_seconds = var.api_ecs_health_check_grace_period_seconds
  enable_execute_command            = true

  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 200

  network_configuration {
    subnets          = var.api_ecs_private_subnet_ids
    security_groups  = concat([aws_security_group.api_task[0].id], var.api_ecs_additional_security_group_ids)
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api[0].arn
    container_name   = trim(var.api_ecs_container_name, " ")
    container_port   = var.api_ecs_container_port
  }

  depends_on = [aws_lb_listener.api_https]

  tags = local.platform_common_tags
}
