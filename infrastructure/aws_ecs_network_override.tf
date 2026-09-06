# Transitional brownfield override.
#
# aws_ecs.tf predates Terraform-owned environment networking and still points
# scheduled EventBridge ECS targets at externally supplied subnet/security-group
# variables. Terraform override semantics replace only the ecs_target nested
# blocks below while preserving the existing resource count/rule/role wiring.
# Remove this file when aws_ecs.tf is reconciled to use the effective network
# locals directly.

resource "aws_cloudwatch_event_target" "daily_ingest_ecs_target" {
  ecs_target {
    launch_type         = "FARGATE"
    task_count          = 1
    task_definition_arn = aws_ecs_task_definition.eo_bmf_ingest_worker[0].arn

    network_configuration {
      subnets          = local.monthly_ingest_private_subnet_ids_effective
      security_groups  = local.monthly_ingest_task_security_group_ids_effective
      assign_public_ip = false
    }
  }
}

resource "aws_cloudwatch_event_target" "form990_ecs_target" {
  ecs_target {
    launch_type         = "FARGATE"
    task_count          = 1
    task_definition_arn = local.monthly_ingest_task_definition_arn_resolved

    network_configuration {
      subnets          = local.monthly_ingest_private_subnet_ids_effective
      security_groups  = local.monthly_ingest_task_security_group_ids_effective
      assign_public_ip = false
    }
  }
}
