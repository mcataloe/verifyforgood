import json
from pathlib import Path


def _render_state_machine_template(*, staging_default_state: str = "InvokeStagingLambda") -> dict:
    content = Path("infrastructure/monthly_ingest_state_machine.asl.json.tftpl").read_text(encoding="utf-8")
    replacements = {
        "workflow_name": "monthly-ingest-prod",
        "workflow_version": "2026-03",
        "app_env": "prod",
        "aws_region": "us-east-1",
        "ecs_cluster_name_reference": "verification-platform-processing-prod",
        "staging_default_state": staging_default_state,
        "staging_lambda_arn": "arn:aws:lambda:us-east-1:123456789012:function:monthly-ingest-staging",
        "staging_lambda_timeout_seconds": "900",
        "endpoint_poll_interval_seconds": "20",
        "endpoint_ready_max_attempts": "30",
        "ecs_cluster_arn": "arn:aws:ecs:us-east-1:123456789012:cluster/monthly-ingest",
        "ecs_task_definition_arn": "arn:aws:ecs:us-east-1:123456789012:task-definition/monthly-ingest:1",
        "ecs_container_name": "monthly-ingest",
        "ecs_task_timeout_seconds": "14400",
        "state_machine_timeout_seconds": "21600",
        "vpc_id": "vpc-12345",
        "subnet_ids_json": json.dumps(["subnet-a", "subnet-b"]),
        "endpoint_security_group_ids_json": json.dumps(["sg-endpoint"]),
        "task_security_group_ids_json": json.dumps(["sg-task"]),
        "retry_interval_seconds": "2",
        "retry_max_attempts": "3",
        "retry_backoff_rate": "2",
    }
    for key, value in replacements.items():
        content = content.replace(f"${{{key}}}", value)
    return json.loads(content)


def test_state_machine_template_renders_valid_json_with_required_integrations():
    definition = _render_state_machine_template()
    states = definition["States"]

    assert definition["StartAt"] == "ValidateRequiredInput"
    assert definition["TimeoutSeconds"] == 21600
    assert states["CreateEcrApiEndpoint"]["Resource"] == "arn:aws:states:::aws-sdk:ec2:createVpcEndpoint"
    assert states["DescribeLogsEndpoint"]["Resource"] == "arn:aws:states:::aws-sdk:ec2:describeVpcEndpoints"
    assert states["DeleteEcrApiEndpoint"]["Resource"] == "arn:aws:states:::aws-sdk:ec2:deleteVpcEndpoints"
    assert states["InvokeStagingLambda"]["Resource"] == "arn:aws:states:::lambda:invoke"
    assert states["RunMonthlyIngestTask"]["Resource"] == "arn:aws:states:::ecs:runTask.sync"


def test_state_machine_template_preserves_shared_cleanup_chain_and_failure_exit():
    definition = _render_state_machine_template()
    states = definition["States"]

    assert states["RecordEcsTaskFailure"]["Next"] == "DeleteLogsEndpointIfPresent"
    assert states["DeleteLogsEndpointIfPresent"]["Default"] == "DeleteLogsEndpoint"
    assert states["DeleteLogsEndpoint"]["Next"] == "DeleteEcrDkrEndpointIfPresent"
    assert states["DeleteEcrDkrEndpoint"]["Next"] == "DeleteEcrApiEndpointIfPresent"
    assert states["DeleteEcrApiEndpoint"]["Next"] == "DidCleanupEncounterErrors"
    assert states["DidCleanupEncounterErrors"]["Choices"][0]["Next"] == "AssembleFailureResult"
    assert states["SerializeFailureResult"]["Next"] == "FailWorkflow"
    assert states["FailWorkflow"]["Type"] == "Fail"


def test_state_machine_template_can_disable_staging_lambda_path_without_breaking_flow():
    definition = _render_state_machine_template(staging_default_state="RecordStagingConfigurationError")
    states = definition["States"]

    assert states["ShouldInvokeStagingLambda"]["Default"] == "RecordStagingConfigurationError"
    assert states["RecordStagingConfigurationFailure"]["Next"] == "DeleteLogsEndpointIfPresent"


def test_step_functions_terraform_wires_role_logging_and_schedule_target():
    content = Path("infrastructure/aws_step_functions.tf").read_text(encoding="utf-8")

    assert 'resource "aws_sfn_state_machine" "monthly_ingest"' in content
    assert 'resource "aws_cloudwatch_log_group" "monthly_ingest_state_machine"' in content
    assert 'resource "aws_iam_role" "monthly_ingest_state_machine"' in content
    assert '"ec2:CreateVpcEndpoint"' in content
    assert '"ec2:DescribeVpcEndpoints"' in content
    assert '"ec2:DeleteVpcEndpoints"' in content
    assert '"ecs:RunTask"' in content
    assert '"iam:PassRole"' in content
    assert '"lambda:InvokeFunction"' in content
    assert "monthly_ingest_staging_lambda_arn_resolved" in content
    assert "monthly_ingest_schedule_source_key_effective" in content
    assert 'resource "aws_cloudwatch_event_target" "monthly_ingest_state_machine_target"' in content
    assert '"states:StartExecution"' in content
    assert "monthly-workflows/pending/${local.monthly_ingest_schedule_job_id}/source.zip" in content


def test_monthly_ingest_lambda_terraform_wires_staging_lambda_resource():
    content = Path("infrastructure/aws_lambda.tf").read_text(encoding="utf-8")

    assert 'resource "aws_lambda_function" "monthly_ingest_staging"' in content
    assert 'handler       = "lambda_monthly_ingest_staging.handler"' in content
    assert 'local.lambda_function_names.monthly_private_ingest_staging' in content
    assert 'FORM990_SOURCE_DOWNLOAD_TIMEOUT_SECONDS = tostring(var.form990_zip_fetch_timeout_seconds)' in content
    assert 'MONTHLY_INGEST_WORKFLOW_NAME            = local.monthly_ingest_workflow_name' in content


def test_monthly_ingest_ecs_terraform_wires_managed_task_definition_and_roles():
    content = Path("infrastructure/aws_ecs.tf").read_text(encoding="utf-8")

    assert 'resource "aws_ecr_repository" "monthly_ingest_worker"' in content
    assert 'resource "aws_cloudwatch_log_group" "monthly_ingest_task"' in content
    assert 'resource "aws_iam_role" "monthly_ingest_task_execution"' in content
    assert 'resource "aws_iam_role" "monthly_ingest_task"' in content
    assert 'resource "aws_ecs_task_definition" "monthly_ingest_worker"' in content
    assert 'requires_compatibilities = ["FARGATE"]' in content
    assert 'ephemeral_storage {' in content
    assert 'monthly_ingest_worker_image_uri_resolved' in content
    assert 'monthly_ingest_task_definition_arn_resolved' in content
    assert 'entryPoint = ["python", "-m", "charity_status_backend.ingest_task.cli"]' in content
    assert 'command    = ["monthly-worker"]' in content
    assert 'FORM990_ZIP_MAX_XML_FILE_SIZE_BYTES' in content


def test_monthly_ingest_variables_capture_existing_infra_references_and_timeouts():
    content = Path("infrastructure/variables.tf").read_text(encoding="utf-8")

    assert 'variable "monthly_ingest_state_machine_enabled"' in content
    assert 'variable "monthly_ingest_vpc_id"' in content
    assert 'variable "monthly_ingest_private_subnet_ids"' in content
    assert 'variable "monthly_ingest_endpoint_security_group_ids"' in content
    assert 'variable "monthly_ingest_task_security_group_ids"' in content
    assert 'variable "monthly_ingest_ecs_cluster_arn"' in content
    assert 'variable "monthly_ingest_task_definition_arn"' in content
    assert 'variable "monthly_ingest_staging_lambda_arn"' in content
    assert 'variable "monthly_ingest_worker_image_uri"' in content
    assert 'variable "monthly_ingest_task_ephemeral_storage_gib"' in content
    assert 'variable "monthly_ingest_task_allowed_bucket_arns"' in content
    assert 'variable "monthly_ingest_endpoint_poll_interval_seconds"' in content
    assert 'variable "monthly_ingest_state_machine_timeout_seconds"' in content


def test_monthly_ingest_docs_describe_permanent_ephemeral_and_troubleshooting_paths():
    architecture = Path("docs/monthly-ingest-architecture.md").read_text(encoding="utf-8")
    runbook = Path("docs/monthly-ingest-runbook.md").read_text(encoding="utf-8")

    assert "Permanent infrastructure remains" in architecture
    assert "Ephemeral infrastructure per run remains" in architecture
    assert "conductor: Step Functions" in architecture
    assert "staging component: the staging Lambda" in architecture
    assert "worker: the ECS Fargate worker" in architecture
    assert "permanent endpoint: S3 gateway endpoint" in runbook
    assert "ephemeral endpoints: `ecr.api`, `ecr.dkr`, and `logs`" in runbook
    assert "Troubleshooting sequence" in runbook


def test_api_ecs_terraform_wires_parallel_runtime_resources():
    content = Path("infrastructure/aws_api_ecs.tf").read_text(encoding="utf-8")
    worker_content = Path("infrastructure/aws_ecs.tf").read_text(encoding="utf-8")

    assert 'resource "aws_ecs_cluster" "api"' in content
    assert "backend_runtime_ecs_cluster_enabled" in content
    assert 'resource "aws_ecr_repository" "api"' in content
    assert 'resource "aws_cloudwatch_log_group" "api_task"' in content
    assert 'resource "aws_security_group" "api_alb"' in content
    assert 'resource "aws_security_group" "api_task"' in content
    assert 'resource "aws_lb" "api"' in content
    assert 'resource "aws_lb_target_group" "api"' in content
    assert 'resource "aws_lb_listener" "api_http"' in content
    assert 'resource "aws_lb_listener" "api_https"' in content
    assert 'resource "aws_iam_role" "api_task_execution"' in content
    assert 'resource "aws_iam_role" "api_task"' in content
    assert 'resource "aws_ecs_task_definition" "api"' in content
    assert 'resource "aws_ecs_service" "api"' in content
    assert 'requires_compatibilities = ["FARGATE"]' in content
    assert 'health_check_grace_period_seconds = var.api_ecs_health_check_grace_period_seconds' in content
    assert 'api_ecs_secret_arns_resolved' in content
    assert 'containerInsights' in content
    assert 'awslogs-stream-prefix = "ecs"' in content

    assert 'resource "aws_ecr_repository" "worker"' in worker_content
    assert 'resource "aws_cloudwatch_log_group" "worker_task"' in worker_content
    assert 'resource "aws_security_group" "worker_task"' in worker_content
    assert 'resource "aws_iam_role" "worker_task_execution"' in worker_content
    assert 'resource "aws_iam_role" "worker_task"' in worker_content
    assert 'resource "aws_ecs_task_definition" "worker"' in worker_content
    assert 'resource "aws_ecs_service" "worker"' in worker_content
    assert 'cluster                = aws_ecs_cluster.api[0].id' in worker_content
    assert 'assign_public_ip = false' in worker_content
    assert 'worker_ecs_container_plaintext_environment' in worker_content
    assert 'worker_ecs_secret_arns_resolved' in worker_content
    assert 'deployment_minimum_healthy_percent = 0' in worker_content
    assert 'deployment_maximum_percent         = 100' in worker_content


def test_api_ecs_variables_outputs_and_parallel_ingress_docs_are_present():
    variables_content = Path("infrastructure/variables.tf").read_text(encoding="utf-8")
    outputs_content = Path("infrastructure/outputs.tf").read_text(encoding="utf-8")
    rds_content = Path("infrastructure/aws_rds.tf").read_text(encoding="utf-8")
    route53_content = Path("infrastructure/aws_route53.tf").read_text(encoding="utf-8")
    gateway_content = Path("infrastructure/aws_api_gateway.tf").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    infra_readme = Path("infrastructure/README.md").read_text(encoding="utf-8")
    ecs_blueprint = Path("docs/implementation/ecs-runtime-migration-blueprint.md").read_text(encoding="utf-8")

    assert 'variable "api_ecs_enabled"' in variables_content
    assert 'variable "api_ecs_vpc_id"' in variables_content
    assert 'variable "api_ecs_public_subnet_ids"' in variables_content
    assert 'variable "api_ecs_private_subnet_ids"' in variables_content
    assert 'variable "api_ecs_image_uri"' in variables_content
    assert 'variable "api_ecs_secret_arns"' in variables_content
    assert 'variable "api_alb_certificate_arn"' in variables_content
    assert 'variable "worker_ecs_enabled"' in variables_content
    assert 'variable "worker_ecs_vpc_id"' in variables_content
    assert 'variable "worker_ecs_private_subnet_ids"' in variables_content
    assert 'variable "worker_ecs_image_uri"' in variables_content
    assert 'variable "worker_ecs_desired_count"' in variables_content
    assert 'variable "worker_ecs_secret_arns"' in variables_content

    assert 'output "api_ecs_cluster_name"' in outputs_content
    assert 'output "api_ecr_repository_url"' in outputs_content
    assert 'output "api_ecs_service_name"' in outputs_content
    assert 'output "api_alb_dns_name"' in outputs_content
    assert 'output "api_alb_target_group_arn"' in outputs_content
    assert 'output "backend_runtime_ecs_cluster_name"' in outputs_content
    assert 'output "worker_ecr_repository_url"' in outputs_content
    assert 'output "worker_ecs_service_name"' in outputs_content
    assert 'output "worker_ecs_task_definition_arn"' in outputs_content
    assert 'output "worker_ecs_task_log_group_name"' in outputs_content

    assert "aws_security_group.api_task[0].id" in rds_content
    assert "aws_security_group.worker_task[0].id" in rds_content
    assert 'resource "aws_api_gateway_domain_name" "api_domain"' in route53_content
    assert 'resource "aws_route53_record" "api_record"' in route53_content
    assert 'name                   = var.api_ecs_enabled ? aws_lb.api[0].dns_name : aws_api_gateway_domain_name.api_domain[0].cloudfront_domain_name' in route53_content
    assert 'zone_id                = var.api_ecs_enabled ? aws_lb.api[0].zone_id : aws_api_gateway_domain_name.api_domain[0].cloudfront_zone_id' in route53_content
    assert 'evaluate_target_health = var.api_ecs_enabled' in route53_content
    assert 'resource "aws_api_gateway_rest_api" "irs_api"' in gateway_content
    assert "primary API ingress is now Route53 -> ALB -> ECS Fargate" in readme
    assert "`backend/worker` -> private ECS service placeholder" in readme
    assert "deprecated rollback path" in readme
    assert "ECS Runtime Mapping" in infra_readme
    assert "`backend/worker`" in infra_readme
    assert "disabled by default" in infra_readme
    assert "Route53 now points the primary API hostname at the public ALB" in infra_readme
    assert "Phase 25C/25D implementation status" in ecs_blueprint
    assert "`backend/worker` -> provisionable ECS Fargate service slot" in ecs_blueprint
    assert "Route53 now points the primary hostname at the ALB" in ecs_blueprint
