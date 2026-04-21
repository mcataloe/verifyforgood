from pathlib import Path


def test_monthly_ingest_ecs_terraform_wires_managed_task_definition_and_roles():
    content = Path("infrastructure/aws_ecs.tf").read_text(encoding="utf-8")

    assert 'resource "aws_ecr_repository" "monthly_ingest_worker"' in content
    assert 'resource "aws_cloudwatch_log_group" "monthly_ingest_task"' in content
    assert 'resource "aws_iam_role" "monthly_ingest_task_execution"' in content
    assert 'resource "aws_iam_role" "monthly_ingest_task"' in content
    assert 'resource "aws_ecs_task_definition" "monthly_ingest_worker"' in content
    assert 'resource "aws_ecs_task_definition" "eo_bmf_ingest_worker"' in content
    assert 'requires_compatibilities = ["FARGATE"]' in content
    assert 'ephemeral_storage {' in content
    assert 'entryPoint = ["python", "-m", "verification_backend.ingest_task.cli"]' in content
    assert 'command    = ["ecs-run"]' in content
    assert 'command    = ["ecs-run-eo-bmf"]' in content


def test_eventbridge_targets_ecs_directly_without_step_functions_or_lambda():
    content = Path("infrastructure/aws_ecs.tf").read_text(encoding="utf-8")

    assert 'resource "aws_iam_role" "ingest_schedule"' in content
    assert 'resource "aws_cloudwatch_event_rule" "daily_ingest"' in content
    assert 'resource "aws_cloudwatch_event_target" "daily_ingest_ecs_target"' in content
    assert 'resource "aws_cloudwatch_event_rule" "form990_schedule"' in content
    assert 'resource "aws_cloudwatch_event_target" "form990_ecs_target"' in content
    assert '"ecs:RunTask"' in content
    assert '"iam:PassRole"' in content
    assert '"events.amazonaws.com"' in content

    assert not Path("infrastructure/aws_step_functions.tf").exists()
    assert not Path("infrastructure/monthly_ingest_state_machine.asl.json.tftpl").exists()


def test_monthly_ingest_variables_and_outputs_drop_staging_lambda_and_step_functions():
    variables_content = Path("infrastructure/variables.tf").read_text(encoding="utf-8")
    outputs_content = Path("infrastructure/outputs.tf").read_text(encoding="utf-8")

    assert 'variable "monthly_ingest_ecs_cluster_arn"' in variables_content
    assert 'variable "monthly_ingest_task_definition_arn"' in variables_content
    assert 'variable "monthly_ingest_state_machine_enabled"' not in variables_content
    assert 'variable "monthly_ingest_staging_lambda_arn"' not in variables_content
    assert 'variable "refresh_lambda_enabled"' not in variables_content
    assert 'variable "form990_worker_timeout_seconds"' not in variables_content
    assert 'output "monthly_ingest_task_definition_arn"' in outputs_content
    assert 'output "monthly_ingest_state_machine_name"' not in outputs_content
    assert 'output "monthly_ingest_state_machine_arn"' not in outputs_content
    assert 'output "monthly_ingest_staging_lambda_arn"' not in outputs_content


def test_route53_points_custom_domain_at_alb_only():
    route53_content = Path("infrastructure/aws_route53.tf").read_text(encoding="utf-8")

    assert 'resource "aws_route53_record" "api_record"' in route53_content
    assert 'name                   = aws_lb.api[0].dns_name' in route53_content
    assert 'zone_id                = aws_lb.api[0].zone_id' in route53_content
    assert 'evaluate_target_health = true' in route53_content
    assert 'aws_api_gateway_domain_name' not in route53_content
    assert not Path("infrastructure/aws_api_gateway.tf").exists()


def test_api_ecs_terraform_wires_alb_runtime_and_ecs_run_task_for_manual_form990():
    api_content = Path("infrastructure/aws_api_ecs.tf").read_text(encoding="utf-8")
    worker_content = Path("infrastructure/aws_ecs.tf").read_text(encoding="utf-8")

    assert 'resource "aws_ecs_cluster" "api"' in api_content
    assert 'resource "aws_lb" "api"' in api_content
    assert 'resource "aws_ecs_service" "api"' in api_content
    assert 'FORM990_RUN_TASK_CLUSTER_ARN' in api_content
    assert 'FORM990_RUN_TASK_DEFINITION_ARN' in api_content
    assert 'FORM990_RUN_TASK_CONTAINER_NAME' in api_content
    assert 'FORM990_RUN_TASK_SUBNET_IDS' in api_content
    assert 'FORM990_RUN_TASK_SECURITY_GROUP_IDS' in api_content
    assert '"ecs:RunTask"' in api_content
    assert '"iam:PassRole"' in api_content

    assert 'resource "aws_ecr_repository" "worker"' in worker_content
    assert 'resource "aws_ecs_service" "worker"' in worker_content
