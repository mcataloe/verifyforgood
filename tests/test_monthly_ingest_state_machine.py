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
    assert 'resource "aws_cloudwatch_event_target" "monthly_ingest_state_machine_target"' in content
    assert '"states:StartExecution"' in content


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
    assert 'variable "monthly_ingest_endpoint_poll_interval_seconds"' in content
    assert 'variable "monthly_ingest_state_machine_timeout_seconds"' in content
