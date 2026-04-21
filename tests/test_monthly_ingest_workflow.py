import json

from verification.ingest import (
    EcsTaskRuntimeContract,
    default_interface_endpoint_services,
    load_monthly_ingest_workflow_config,
    shape_step_function_input,
    validate_step_function_input_payload,
)


def test_shape_step_function_input_defaults_correlation_id_to_job_id():
    payload = shape_step_function_input(
        archive_identity="form990/raw-sources/2026/zip_archive/2026_teos_xml_02a/sig-1/2026_TEOS_XML_02A.zip",
        archive_url="https://example.org/2026_TEOS_XML_02A.zip",
        job_id="job-123",
    )

    assert payload.to_dict() == {
        "archive_identity": "form990/raw-sources/2026/zip_archive/2026_teos_xml_02a/sig-1/2026_TEOS_XML_02A.zip",
        "archive_url": "https://example.org/2026_TEOS_XML_02A.zip",
        "job_id": "job-123",
        "correlation_id": "job-123",
        "workflow_version": "2026-03",
    }


def test_validate_step_function_input_payload_reports_missing_required_fields():
    errors = validate_step_function_input_payload(
        {
            "archive_identity": "",
            "archive_url": "https://example.org/2026_TEOS_XML_02A.zip",
            "job_id": "job-123",
            "correlation_id": "",
            "workflow_version": "2026-03",
        }
    )

    assert "archive_identity is required" in errors
    assert "correlation_id is required" in errors


def test_shape_step_function_input_supports_optional_schedule_context():
    payload = shape_step_function_input(
        archive_identity="form990/raw-sources/2026/zip_archive/2026_teos_xml_02a/sig-1/2026_TEOS_XML_02A.zip",
        archive_url="https://example.org/2026_TEOS_XML_02A.zip",
        job_id="job-123",
        schedule_context={"trigger": "eventbridge"},
    )

    assert payload.to_dict()["schedule_context"] == {"trigger": "eventbridge"}
    assert validate_step_function_input_payload(payload.to_dict()) == []


def test_ecs_task_runtime_contract_builds_valid_environment():
    workflow_input = shape_step_function_input(
        archive_identity="form990/raw-sources/2026/zip_archive/2026_teos_xml_02a/sig-1/2026_TEOS_XML_02A.zip",
        archive_url="https://example.org/2026_TEOS_XML_02A.zip",
        job_id="job-123",
        correlation_id="corr-123",
    )
    contract = EcsTaskRuntimeContract()

    env = contract.build_environment(workflow_input, workflow_name="monthly-ingest-prod")

    assert contract.validate_environment(env) == []
    payload = json.loads(env["MONTHLY_INGEST_INPUT_JSON"])
    assert payload["job_id"] == "job-123"
    assert payload["correlation_id"] == "corr-123"
    assert env["MONTHLY_INGEST_WORKFLOW_NAME"] == "monthly-ingest-prod"
    assert env["MONTHLY_INGEST_ARCHIVE_IDENTITY"] == workflow_input.archive_identity
    assert env["MONTHLY_INGEST_ARCHIVE_URL"] == workflow_input.archive_url


def test_monthly_ingest_workflow_config_loads_env_and_resolves_endpoint_services():
    config = load_monthly_ingest_workflow_config(
        {
            "APP_ENV": "prod",
            "AWS_REGION": "us-west-2",
            "MONTHLY_INGEST_WORKFLOW_BASENAME": "monthly-zip",
            "MONTHLY_INGEST_ECS_CLUSTER_NAME": "shared-ingest-cluster",
            "MONTHLY_INGEST_RETRY_INTERVAL_SECONDS": "45",
            "MONTHLY_INGEST_RETRY_MAX_ATTEMPTS": "4",
            "MONTHLY_INGEST_RETRY_BACKOFF_RATE": "2.5",
            "MONTHLY_INGEST_ENDPOINT_POLL_INTERVAL_SECONDS": "15",
            "MONTHLY_INGEST_ENDPOINT_READY_MAX_ATTEMPTS": "12",
            "MONTHLY_INGEST_STAGING_LAMBDA_TIMEOUT_SECONDS": "600",
            "MONTHLY_INGEST_ECS_TASK_TIMEOUT_SECONDS": "3600",
            "MONTHLY_INGEST_STATE_MACHINE_TIMEOUT_SECONDS": "4200",
        }
    )

    assert config.validate() == []
    assert config.workflow_name == "monthly-zip-prod"
    assert config.aws_region == "us-west-2"
    assert config.ecs_cluster_name_reference == "shared-ingest-cluster"
    assert config.step_function_log_group_name == "/aws/vendedlogs/states/monthly-zip-prod"
    assert config.ecs_task_log_group_name == "/aws/ecs/monthly-zip-prod"
    assert config.retry.interval_seconds == 45
    assert config.retry.max_attempts == 4
    assert config.retry.backoff_rate == 2.5
    assert config.endpoint_poll_interval_seconds == 15
    assert config.endpoint_ready_max_attempts == 12
    assert config.staging_lambda_timeout_seconds == 600
    assert config.ecs_task_timeout_seconds == 3600
    assert config.state_machine_timeout_seconds == 4200
    assert tuple(endpoint.service_identifier for endpoint in config.endpoint_services) == ("ecr.api", "ecr.dkr", "logs")


def test_interface_endpoint_contract_is_environment_aware():
    endpoint = default_interface_endpoint_services()[0]

    assert endpoint.service_name("us-east-1") == "com.amazonaws.us-east-1.ecr.api"
    assert endpoint.build_tags(
        workflow_name="monthly-ingest-dev",
        environment="dev",
        job_id="job-123",
        correlation_id="corr-123",
    ) == {
        "Name": "monthly-ingest-dev-ecr-api",
        "workflow_name": "monthly-ingest-dev",
        "workflow_environment": "dev",
        "endpoint_lifecycle": "ephemeral",
        "endpoint_service": "ecr.api",
        "job_id": "job-123",
        "correlation_id": "corr-123",
    }
