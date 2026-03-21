data "aws_caller_identity" "current" {}

locals {
  monthly_ingest_workflow_name              = trim(var.monthly_ingest_workflow_name, " ") != "" ? trim(var.monthly_ingest_workflow_name, " ") : "${var.monthly_ingest_workflow_basename}-${local.environment_slug}"
  monthly_ingest_ecs_cluster_name_reference = trim(var.monthly_ingest_ecs_cluster_name, " ") != "" ? trim(var.monthly_ingest_ecs_cluster_name, " ") : local.ecs_cluster_name
  monthly_ingest_schedule_job_id            = trim(var.monthly_ingest_schedule_job_id, " ") != "" ? trim(var.monthly_ingest_schedule_job_id, " ") : "scheduled-${local.environment_slug}"
  monthly_ingest_schedule_correlation_id    = trim(var.monthly_ingest_schedule_correlation_id, " ") != "" ? trim(var.monthly_ingest_schedule_correlation_id, " ") : local.monthly_ingest_schedule_job_id
  monthly_ingest_schedule_context           = try(jsondecode(var.monthly_ingest_schedule_context_json), {})
  monthly_ingest_staging_lambda_configured  = trim(var.monthly_ingest_staging_lambda_arn, " ") != ""
  monthly_ingest_pass_role_arns             = compact([trim(var.monthly_ingest_task_execution_role_arn, " "), trim(var.monthly_ingest_task_role_arn, " ")])
  monthly_ingest_schedule_enabled = (
    var.monthly_ingest_state_machine_enabled
    && trim(var.monthly_ingest_schedule_expression, " ") != ""
    && trim(var.monthly_ingest_schedule_source_bucket, " ") != ""
    && trim(var.monthly_ingest_schedule_source_key, " ") != ""
    && trim(var.monthly_ingest_schedule_destination_bucket, " ") != ""
    && trim(var.monthly_ingest_schedule_destination_prefix, " ") != ""
  )
  monthly_ingest_schedule_input = {
    source_bucket      = trim(var.monthly_ingest_schedule_source_bucket, " ")
    source_key         = trim(var.monthly_ingest_schedule_source_key, " ")
    destination_bucket = trim(var.monthly_ingest_schedule_destination_bucket, " ")
    destination_prefix = trim(var.monthly_ingest_schedule_destination_prefix, " ")
    job_id             = local.monthly_ingest_schedule_job_id
    correlation_id     = local.monthly_ingest_schedule_correlation_id
    workflow_version   = var.monthly_ingest_workflow_version
    skip_staging       = var.monthly_ingest_schedule_skip_staging
    schedule_context = merge(
      local.monthly_ingest_schedule_context,
      {
        trigger            = "eventbridge"
        environment        = var.environment
        schedule_rule_name = local.monthly_ingest_schedule_rule_name
      }
    )
  }
  monthly_ingest_state_machine_definition = templatefile("${path.module}/monthly_ingest_state_machine.asl.json.tftpl", {
    workflow_name                    = local.monthly_ingest_workflow_name
    workflow_version                 = var.monthly_ingest_workflow_version
    app_env                          = var.environment
    aws_region                       = var.aws_region
    ecs_cluster_name_reference       = local.monthly_ingest_ecs_cluster_name_reference
    staging_lambda_enabled           = local.monthly_ingest_staging_lambda_configured
    staging_default_state            = local.monthly_ingest_staging_lambda_configured ? "InvokeStagingLambda" : "RecordStagingConfigurationError"
    staging_lambda_arn               = trim(var.monthly_ingest_staging_lambda_arn, " ")
    staging_lambda_timeout_seconds   = var.monthly_ingest_staging_lambda_timeout_seconds
    endpoint_poll_interval_seconds   = var.monthly_ingest_endpoint_poll_interval_seconds
    endpoint_ready_max_attempts      = var.monthly_ingest_endpoint_ready_max_attempts
    ecs_cluster_arn                  = trim(var.monthly_ingest_ecs_cluster_arn, " ")
    ecs_task_definition_arn          = trim(var.monthly_ingest_task_definition_arn, " ")
    ecs_container_name               = trim(var.monthly_ingest_container_name, " ")
    ecs_task_timeout_seconds         = var.monthly_ingest_ecs_task_timeout_seconds
    state_machine_timeout_seconds    = var.monthly_ingest_state_machine_timeout_seconds
    vpc_id                           = trim(var.monthly_ingest_vpc_id, " ")
    subnet_ids_json                  = jsonencode(var.monthly_ingest_private_subnet_ids)
    endpoint_security_group_ids_json = jsonencode(var.monthly_ingest_endpoint_security_group_ids)
    task_security_group_ids_json     = jsonencode(var.monthly_ingest_task_security_group_ids)
    retry_interval_seconds           = var.monthly_ingest_retry_interval_seconds
    retry_max_attempts               = var.monthly_ingest_retry_max_attempts
    retry_backoff_rate               = var.monthly_ingest_retry_backoff_rate
  })
}

resource "aws_cloudwatch_log_group" "monthly_ingest_state_machine" {
  count = var.monthly_ingest_state_machine_enabled ? 1 : 0

  name = "/aws/vendedlogs/states/${local.monthly_ingest_workflow_name}"
  tags = local.platform_common_tags
}

resource "aws_iam_role" "monthly_ingest_state_machine" {
  count = var.monthly_ingest_state_machine_enabled ? 1 : 0

  name = local.monthly_ingest_state_machine_role_name

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "states.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy" "monthly_ingest_state_machine" {
  count = var.monthly_ingest_state_machine_enabled ? 1 : 0

  name = "${local.monthly_ingest_state_machine_role_name}-policy"
  role = aws_iam_role.monthly_ingest_state_machine[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat(
      [
        {
          Sid    = "VpcEndpointLifecycle"
          Effect = "Allow"
          Action = [
            "ec2:CreateVpcEndpoint",
            "ec2:DescribeVpcEndpoints",
            "ec2:DeleteVpcEndpoints"
          ]
          Resource = "*"
        },
        {
          Sid    = "RunMonthlyIngestTask"
          Effect = "Allow"
          Action = [
            "ecs:RunTask",
            "ecs:DescribeTasks",
            "ecs:StopTask"
          ]
          Resource = "*"
        },
        {
          Sid    = "EcsSyncEventBridge"
          Effect = "Allow"
          Action = [
            "events:PutRule",
            "events:PutTargets",
            "events:DescribeRule"
          ]
          Resource = "arn:aws:events:${var.aws_region}:${data.aws_caller_identity.current.account_id}:rule/StepFunctionsGetEventsForECSTaskRule"
        },
        {
          Sid    = "StepFunctionsLogging"
          Effect = "Allow"
          Action = [
            "logs:CreateLogDelivery",
            "logs:GetLogDelivery",
            "logs:UpdateLogDelivery",
            "logs:DeleteLogDelivery",
            "logs:ListLogDeliveries",
            "logs:PutResourcePolicy",
            "logs:DescribeResourcePolicies",
            "logs:DescribeLogGroups"
          ]
          Resource = "*"
        }
      ],
      local.monthly_ingest_staging_lambda_configured ? [
        {
          Sid      = "InvokeStagingLambda"
          Effect   = "Allow"
          Action   = ["lambda:InvokeFunction"]
          Resource = [trim(var.monthly_ingest_staging_lambda_arn, " ")]
        }
      ] : [],
      length(local.monthly_ingest_pass_role_arns) > 0 ? [
        {
          Sid      = "PassMonthlyIngestTaskRoles"
          Effect   = "Allow"
          Action   = ["iam:PassRole"]
          Resource = local.monthly_ingest_pass_role_arns
          Condition = {
            StringEquals = {
              "iam:PassedToService" = "ecs-tasks.amazonaws.com"
            }
          }
        }
      ] : []
    )
  })
}

resource "aws_sfn_state_machine" "monthly_ingest" {
  count = var.monthly_ingest_state_machine_enabled ? 1 : 0

  name       = local.monthly_ingest_state_machine_name
  role_arn   = aws_iam_role.monthly_ingest_state_machine[0].arn
  type       = "STANDARD"
  definition = local.monthly_ingest_state_machine_definition

  logging_configuration {
    include_execution_data = true
    level                  = "ALL"
    log_destination        = "${aws_cloudwatch_log_group.monthly_ingest_state_machine[0].arn}:*"
  }

  tags = local.platform_common_tags

  lifecycle {
    precondition {
      condition     = trim(var.monthly_ingest_vpc_id, " ") != ""
      error_message = "monthly_ingest_vpc_id must be set when monthly_ingest_state_machine_enabled=true."
    }
    precondition {
      condition     = length(var.monthly_ingest_private_subnet_ids) > 0
      error_message = "monthly_ingest_private_subnet_ids must contain at least one private subnet when monthly_ingest_state_machine_enabled=true."
    }
    precondition {
      condition     = length(var.monthly_ingest_endpoint_security_group_ids) > 0
      error_message = "monthly_ingest_endpoint_security_group_ids must contain at least one security group when monthly_ingest_state_machine_enabled=true."
    }
    precondition {
      condition     = length(var.monthly_ingest_task_security_group_ids) > 0
      error_message = "monthly_ingest_task_security_group_ids must contain at least one security group when monthly_ingest_state_machine_enabled=true."
    }
    precondition {
      condition     = trim(var.monthly_ingest_ecs_cluster_arn, " ") != ""
      error_message = "monthly_ingest_ecs_cluster_arn must be set when monthly_ingest_state_machine_enabled=true."
    }
    precondition {
      condition     = trim(var.monthly_ingest_task_definition_arn, " ") != ""
      error_message = "monthly_ingest_task_definition_arn must be set when monthly_ingest_state_machine_enabled=true."
    }
  }
}

resource "aws_iam_role" "monthly_ingest_schedule" {
  count = local.monthly_ingest_schedule_enabled ? 1 : 0

  name = local.monthly_ingest_schedule_role_name

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

resource "aws_iam_role_policy" "monthly_ingest_schedule" {
  count = local.monthly_ingest_schedule_enabled ? 1 : 0

  name = "${local.monthly_ingest_schedule_role_name}-policy"
  role = aws_iam_role.monthly_ingest_schedule[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["states:StartExecution"]
      Resource = [aws_sfn_state_machine.monthly_ingest[0].arn]
    }]
  })
}

resource "aws_cloudwatch_event_rule" "monthly_ingest_schedule" {
  count = local.monthly_ingest_schedule_enabled ? 1 : 0

  name                = local.monthly_ingest_schedule_rule_name
  schedule_expression = var.monthly_ingest_schedule_expression
}

resource "aws_cloudwatch_event_target" "monthly_ingest_state_machine_target" {
  count = local.monthly_ingest_schedule_enabled ? 1 : 0

  rule      = aws_cloudwatch_event_rule.monthly_ingest_schedule[0].name
  target_id = "monthly-ingest"
  arn       = aws_sfn_state_machine.monthly_ingest[0].arn
  role_arn  = aws_iam_role.monthly_ingest_schedule[0].arn
  input     = jsonencode(local.monthly_ingest_schedule_input)
}
