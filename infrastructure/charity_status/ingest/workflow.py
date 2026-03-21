from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping


DEFAULT_MONTHLY_INGEST_WORKFLOW_BASENAME = "monthly-ingest"
DEFAULT_MONTHLY_INGEST_WORKFLOW_VERSION = "2026-03"
DEFAULT_APP_ENV = "dev"
DEFAULT_AWS_REGION = "us-east-1"
DEFAULT_ECS_CLUSTER_NAME_REFERENCE = "resource_names.ecs_cluster"
DEFAULT_STEP_FUNCTION_LOG_GROUP_PREFIX = "/aws/vendedlogs/states"
DEFAULT_ECS_LOG_GROUP_PREFIX = "/aws/ecs"
DEFAULT_ENDPOINT_POLL_INTERVAL_SECONDS = 20
DEFAULT_ENDPOINT_READY_MAX_ATTEMPTS = 30
DEFAULT_STAGING_LAMBDA_TIMEOUT_SECONDS = 900
DEFAULT_ECS_TASK_TIMEOUT_SECONDS = 14400
DEFAULT_STATE_MACHINE_TIMEOUT_SECONDS = 21600

STEP_FUNCTION_INPUT_FIELDS: tuple[str, ...] = (
    "source_bucket",
    "source_key",
    "destination_bucket",
    "destination_prefix",
    "job_id",
    "correlation_id",
    "workflow_version",
)
STEP_FUNCTION_OPTIONAL_FIELDS: tuple[str, ...] = (
    "schedule_context",
    "skip_staging",
)

ECS_TASK_REQUIRED_ENV_VARS: tuple[str, ...] = (
    "MONTHLY_INGEST_WORKFLOW_NAME",
    "MONTHLY_INGEST_WORKFLOW_VERSION",
    "MONTHLY_INGEST_JOB_ID",
    "MONTHLY_INGEST_CORRELATION_ID",
    "MONTHLY_INGEST_SOURCE_BUCKET",
    "MONTHLY_INGEST_SOURCE_KEY",
    "MONTHLY_INGEST_DESTINATION_BUCKET",
    "MONTHLY_INGEST_DESTINATION_PREFIX",
    "MONTHLY_INGEST_INPUT_JSON",
)


@dataclass(frozen=True)
class MonthlyIngestWorkflowInput:
    source_bucket: str
    source_key: str
    destination_bucket: str
    destination_prefix: str
    job_id: str
    correlation_id: str
    workflow_version: str = DEFAULT_MONTHLY_INGEST_WORKFLOW_VERSION
    schedule_context: Mapping[str, Any] | None = None
    skip_staging: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "source_bucket": self.source_bucket,
            "source_key": self.source_key,
            "destination_bucket": self.destination_bucket,
            "destination_prefix": self.destination_prefix,
            "job_id": self.job_id,
            "correlation_id": self.correlation_id,
            "workflow_version": self.workflow_version,
        }
        if isinstance(self.schedule_context, Mapping) and self.schedule_context:
            payload["schedule_context"] = dict(self.schedule_context)
        if self.skip_staging:
            payload["skip_staging"] = True
        return payload

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "MonthlyIngestWorkflowInput":
        errors = validate_step_function_input_payload(payload)
        if errors:
            raise ValueError("; ".join(errors))
        return cls(
            source_bucket=_clean_text(payload.get("source_bucket")) or "",
            source_key=_clean_text(payload.get("source_key")) or "",
            destination_bucket=_clean_text(payload.get("destination_bucket")) or "",
            destination_prefix=_clean_text(payload.get("destination_prefix")) or "",
            job_id=_clean_text(payload.get("job_id")) or "",
            correlation_id=_clean_text(payload.get("correlation_id")) or "",
            workflow_version=_clean_text(payload.get("workflow_version")) or DEFAULT_MONTHLY_INGEST_WORKFLOW_VERSION,
            schedule_context=_mapping_or_none(payload.get("schedule_context")),
            skip_staging=_coerce_bool(payload.get("skip_staging"), default=False, field_name="skip_staging"),
        )


@dataclass(frozen=True)
class WorkflowRetryConfig:
    interval_seconds: int = 30
    max_attempts: int = 3
    backoff_rate: float = 2.0

    def validate(self) -> list[str]:
        errors: list[str] = []
        if int(self.interval_seconds) < 1:
            errors.append("retry interval_seconds must be at least 1")
        if int(self.max_attempts) < 1:
            errors.append("retry max_attempts must be at least 1")
        if float(self.backoff_rate) < 1:
            errors.append("retry backoff_rate must be at least 1")
        return errors


@dataclass(frozen=True)
class EcsTaskOutputArtifact:
    field_name: str
    suffix: str
    description: str
    required: bool = True

    def key_for(self, destination_prefix: str, job_id: str) -> str:
        return f"{workflow_job_prefix(destination_prefix, job_id)}/{self.suffix.strip('/')}"


@dataclass(frozen=True)
class EcsTaskRuntimeContract:
    required_environment_variables: tuple[str, ...] = ECS_TASK_REQUIRED_ENV_VARS
    expected_output_artifacts: tuple[EcsTaskOutputArtifact, ...] = field(
        default_factory=lambda: (
            EcsTaskOutputArtifact(
                field_name="manifest_s3_key",
                suffix="manifest.json",
                description="Task-level manifest describing processed artifacts for the job.",
            ),
            EcsTaskOutputArtifact(
                field_name="artifact_index_s3_key",
                suffix="artifacts.json",
                description="Index of downstream S3 artifacts produced by the task.",
            ),
            EcsTaskOutputArtifact(
                field_name="summary_s3_key",
                suffix="summary.json",
                description="Compact task summary for orchestration status checks and retries.",
            ),
        )
    )

    def validate_payload(self, payload: Mapping[str, Any]) -> list[str]:
        return validate_step_function_input_payload(payload)

    def build_environment(
        self,
        workflow_input: MonthlyIngestWorkflowInput | Mapping[str, Any],
        *,
        workflow_name: str,
    ) -> dict[str, str]:
        contract_input = (
            workflow_input
            if isinstance(workflow_input, MonthlyIngestWorkflowInput)
            else MonthlyIngestWorkflowInput.from_mapping(workflow_input)
        )
        payload = contract_input.to_dict()
        env = {
            "MONTHLY_INGEST_WORKFLOW_NAME": workflow_name,
            "MONTHLY_INGEST_WORKFLOW_VERSION": contract_input.workflow_version,
            "MONTHLY_INGEST_JOB_ID": contract_input.job_id,
            "MONTHLY_INGEST_CORRELATION_ID": contract_input.correlation_id,
            "MONTHLY_INGEST_SOURCE_BUCKET": contract_input.source_bucket,
            "MONTHLY_INGEST_SOURCE_KEY": contract_input.source_key,
            "MONTHLY_INGEST_DESTINATION_BUCKET": contract_input.destination_bucket,
            "MONTHLY_INGEST_DESTINATION_PREFIX": contract_input.destination_prefix,
            "MONTHLY_INGEST_INPUT_JSON": json.dumps(payload, sort_keys=True),
        }
        return env

    def validate_environment(self, env: Mapping[str, str]) -> list[str]:
        errors: list[str] = []
        for key in self.required_environment_variables:
            if not _clean_text(env.get(key)):
                errors.append(f"{key} is required")
        raw_payload = _clean_text(env.get("MONTHLY_INGEST_INPUT_JSON"))
        if raw_payload:
            try:
                payload = json.loads(raw_payload)
            except json.JSONDecodeError:
                errors.append("MONTHLY_INGEST_INPUT_JSON must be valid JSON")
            else:
                if not isinstance(payload, dict):
                    errors.append("MONTHLY_INGEST_INPUT_JSON must decode to an object")
                else:
                    errors.extend(validate_step_function_input_payload(payload))
        return errors


@dataclass(frozen=True)
class VpcEndpointServiceConfig:
    service_identifier: str
    lifecycle: str = "ephemeral"
    endpoint_type: str = "Interface"
    private_dns_enabled: bool = True
    required_for: tuple[str, ...] = ()

    def service_name(self, region: str) -> str:
        cleaned_region = _clean_text(region) or DEFAULT_AWS_REGION
        return f"com.amazonaws.{cleaned_region}.{self.service_identifier}"

    def build_tags(
        self,
        *,
        workflow_name: str,
        environment: str,
        job_id: str | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, str]:
        tags = {
            "Name": f"{workflow_name}-{self.service_identifier.replace('.', '-')}",
            "workflow_name": workflow_name,
            "workflow_environment": environment,
            "endpoint_lifecycle": self.lifecycle,
            "endpoint_service": self.service_identifier,
        }
        if _clean_text(job_id):
            tags["job_id"] = str(job_id).strip()
        if _clean_text(correlation_id):
            tags["correlation_id"] = str(correlation_id).strip()
        return tags


@dataclass(frozen=True)
class MonthlyIngestWorkflowConfig:
    workflow_name: str
    workflow_version: str
    app_env: str
    aws_region: str
    ecs_cluster_name_reference: str
    step_function_log_group_name: str
    ecs_task_log_group_name: str
    endpoint_poll_interval_seconds: int = DEFAULT_ENDPOINT_POLL_INTERVAL_SECONDS
    endpoint_ready_max_attempts: int = DEFAULT_ENDPOINT_READY_MAX_ATTEMPTS
    staging_lambda_timeout_seconds: int = DEFAULT_STAGING_LAMBDA_TIMEOUT_SECONDS
    ecs_task_timeout_seconds: int = DEFAULT_ECS_TASK_TIMEOUT_SECONDS
    state_machine_timeout_seconds: int = DEFAULT_STATE_MACHINE_TIMEOUT_SECONDS
    endpoint_services: tuple[VpcEndpointServiceConfig, ...] = field(default_factory=tuple)
    retry: WorkflowRetryConfig = field(default_factory=WorkflowRetryConfig)
    permanent_network_dependencies: tuple[str, ...] = ("s3_gateway",)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not _clean_text(self.workflow_name):
            errors.append("workflow_name is required")
        if not _clean_text(self.workflow_version):
            errors.append("workflow_version is required")
        if not _clean_text(self.app_env):
            errors.append("app_env is required")
        if not _clean_text(self.aws_region):
            errors.append("aws_region is required")
        if not _clean_text(self.ecs_cluster_name_reference):
            errors.append("ecs_cluster_name_reference is required")
        if not _clean_text(self.step_function_log_group_name):
            errors.append("step_function_log_group_name is required")
        if not _clean_text(self.ecs_task_log_group_name):
            errors.append("ecs_task_log_group_name is required")
        if int(self.endpoint_poll_interval_seconds) < 1:
            errors.append("endpoint_poll_interval_seconds must be at least 1")
        if int(self.endpoint_ready_max_attempts) < 1:
            errors.append("endpoint_ready_max_attempts must be at least 1")
        if int(self.staging_lambda_timeout_seconds) < 1:
            errors.append("staging_lambda_timeout_seconds must be at least 1")
        if int(self.ecs_task_timeout_seconds) < 1:
            errors.append("ecs_task_timeout_seconds must be at least 1")
        if int(self.state_machine_timeout_seconds) < 1:
            errors.append("state_machine_timeout_seconds must be at least 1")
        errors.extend(self.retry.validate())
        for endpoint in self.endpoint_services:
            if not _clean_text(endpoint.service_identifier):
                errors.append("endpoint service_identifier is required")
            if endpoint.endpoint_type != "Interface":
                errors.append(f"{endpoint.service_identifier} endpoint_type must remain Interface")
            if endpoint.lifecycle != "ephemeral":
                errors.append(f"{endpoint.service_identifier} lifecycle must remain ephemeral")
        return errors

    def endpoint(self, service_identifier: str) -> VpcEndpointServiceConfig:
        normalized = str(service_identifier or "").strip().lower()
        for endpoint in self.endpoint_services:
            if endpoint.service_identifier.lower() == normalized:
                return endpoint
        raise KeyError(service_identifier)


def shape_step_function_input(
    *,
    source_bucket: str,
    source_key: str,
    destination_bucket: str,
    destination_prefix: str,
    job_id: str,
    correlation_id: str | None = None,
    workflow_version: str = DEFAULT_MONTHLY_INGEST_WORKFLOW_VERSION,
    schedule_context: Mapping[str, Any] | None = None,
    skip_staging: bool = False,
) -> MonthlyIngestWorkflowInput:
    payload: dict[str, Any] = {
        "source_bucket": source_bucket,
        "source_key": source_key,
        "destination_bucket": destination_bucket,
        "destination_prefix": destination_prefix,
        "job_id": job_id,
        "correlation_id": correlation_id or job_id,
        "workflow_version": workflow_version,
    }
    if isinstance(schedule_context, Mapping):
        payload["schedule_context"] = dict(schedule_context)
    if skip_staging:
        payload["skip_staging"] = True
    return MonthlyIngestWorkflowInput.from_mapping(payload)


def validate_step_function_input_payload(payload: Mapping[str, Any] | None) -> list[str]:
    if not isinstance(payload, Mapping):
        return ["step function input payload must be an object"]
    errors: list[str] = []
    for key in STEP_FUNCTION_INPUT_FIELDS:
        if not _clean_text(payload.get(key)):
            errors.append(f"{key} is required")
    schedule_context = payload.get("schedule_context")
    if schedule_context is not None and not isinstance(schedule_context, Mapping):
        errors.append("schedule_context must be an object when provided")
    skip_staging = payload.get("skip_staging")
    if skip_staging is not None and not isinstance(skip_staging, bool):
        try:
            _coerce_bool(skip_staging, default=False, field_name="skip_staging")
        except ValueError as exc:
            errors.append(str(exc))
    return errors


def workflow_job_prefix(destination_prefix: str, job_id: str) -> str:
    base = str(destination_prefix or "").strip().strip("/")
    job = _safe_path_segment(job_id, default="unknown-job")
    if not base:
        return f"monthly-workflows/jobs/{job}"
    return f"{base}/monthly-workflows/jobs/{job}"


def workflow_manifest_key(destination_prefix: str, job_id: str) -> str:
    return f"{workflow_job_prefix(destination_prefix, job_id)}/manifest.json"


def workflow_artifact_index_key(destination_prefix: str, job_id: str) -> str:
    return f"{workflow_job_prefix(destination_prefix, job_id)}/artifacts.json"


def workflow_summary_key(destination_prefix: str, job_id: str) -> str:
    return f"{workflow_job_prefix(destination_prefix, job_id)}/summary.json"


def default_interface_endpoint_services() -> tuple[VpcEndpointServiceConfig, ...]:
    return (
        VpcEndpointServiceConfig(
            service_identifier="ecr.api",
            required_for=("ecs_image_manifest_resolution",),
        ),
        VpcEndpointServiceConfig(
            service_identifier="ecr.dkr",
            required_for=("ecs_image_layer_download",),
        ),
        VpcEndpointServiceConfig(
            service_identifier="logs",
            required_for=("ecs_awslogs_driver",),
        ),
    )


def default_step_function_log_group_name(workflow_name: str) -> str:
    return f"{DEFAULT_STEP_FUNCTION_LOG_GROUP_PREFIX}/{workflow_name}"


def default_ecs_task_log_group_name(workflow_name: str) -> str:
    return f"{DEFAULT_ECS_LOG_GROUP_PREFIX}/{workflow_name}"


def load_monthly_ingest_workflow_config(env: Mapping[str, str] | None = None) -> MonthlyIngestWorkflowConfig:
    source = env or {}
    app_env = _clean_text(source.get("APP_ENV")) or DEFAULT_APP_ENV
    aws_region = _clean_text(source.get("AWS_REGION")) or _clean_text(source.get("AWS_DEFAULT_REGION")) or DEFAULT_AWS_REGION
    workflow_basename = _clean_text(source.get("MONTHLY_INGEST_WORKFLOW_BASENAME")) or DEFAULT_MONTHLY_INGEST_WORKFLOW_BASENAME
    workflow_name = _clean_text(source.get("MONTHLY_INGEST_WORKFLOW_NAME")) or f"{workflow_basename}-{app_env}"
    workflow_version = _clean_text(source.get("MONTHLY_INGEST_WORKFLOW_VERSION")) or DEFAULT_MONTHLY_INGEST_WORKFLOW_VERSION
    ecs_cluster_name_reference = (
        _clean_text(source.get("MONTHLY_INGEST_ECS_CLUSTER_NAME"))
        or _clean_text(source.get("ECS_CLUSTER_NAME"))
        or DEFAULT_ECS_CLUSTER_NAME_REFERENCE
    )
    step_function_log_group_name = (
        _clean_text(source.get("MONTHLY_INGEST_STEP_FUNCTION_LOG_GROUP_NAME"))
        or default_step_function_log_group_name(workflow_name)
    )
    ecs_task_log_group_name = (
        _clean_text(source.get("MONTHLY_INGEST_ECS_LOG_GROUP_NAME"))
        or default_ecs_task_log_group_name(workflow_name)
    )
    retry = WorkflowRetryConfig(
        interval_seconds=_positive_int(
            source.get("MONTHLY_INGEST_RETRY_INTERVAL_SECONDS"),
            default=30,
            field_name="MONTHLY_INGEST_RETRY_INTERVAL_SECONDS",
        ),
        max_attempts=_positive_int(
            source.get("MONTHLY_INGEST_RETRY_MAX_ATTEMPTS"),
            default=3,
            field_name="MONTHLY_INGEST_RETRY_MAX_ATTEMPTS",
        ),
        backoff_rate=_positive_float(
            source.get("MONTHLY_INGEST_RETRY_BACKOFF_RATE"),
            default=2.0,
            field_name="MONTHLY_INGEST_RETRY_BACKOFF_RATE",
        ),
    )
    return MonthlyIngestWorkflowConfig(
        workflow_name=workflow_name,
        workflow_version=workflow_version,
        app_env=app_env,
        aws_region=aws_region,
        ecs_cluster_name_reference=ecs_cluster_name_reference,
        step_function_log_group_name=step_function_log_group_name,
        ecs_task_log_group_name=ecs_task_log_group_name,
        endpoint_poll_interval_seconds=_positive_int(
            source.get("MONTHLY_INGEST_ENDPOINT_POLL_INTERVAL_SECONDS"),
            default=DEFAULT_ENDPOINT_POLL_INTERVAL_SECONDS,
            field_name="MONTHLY_INGEST_ENDPOINT_POLL_INTERVAL_SECONDS",
        ),
        endpoint_ready_max_attempts=_positive_int(
            source.get("MONTHLY_INGEST_ENDPOINT_READY_MAX_ATTEMPTS"),
            default=DEFAULT_ENDPOINT_READY_MAX_ATTEMPTS,
            field_name="MONTHLY_INGEST_ENDPOINT_READY_MAX_ATTEMPTS",
        ),
        staging_lambda_timeout_seconds=_positive_int(
            source.get("MONTHLY_INGEST_STAGING_LAMBDA_TIMEOUT_SECONDS"),
            default=DEFAULT_STAGING_LAMBDA_TIMEOUT_SECONDS,
            field_name="MONTHLY_INGEST_STAGING_LAMBDA_TIMEOUT_SECONDS",
        ),
        ecs_task_timeout_seconds=_positive_int(
            source.get("MONTHLY_INGEST_ECS_TASK_TIMEOUT_SECONDS"),
            default=DEFAULT_ECS_TASK_TIMEOUT_SECONDS,
            field_name="MONTHLY_INGEST_ECS_TASK_TIMEOUT_SECONDS",
        ),
        state_machine_timeout_seconds=_positive_int(
            source.get("MONTHLY_INGEST_STATE_MACHINE_TIMEOUT_SECONDS"),
            default=DEFAULT_STATE_MACHINE_TIMEOUT_SECONDS,
            field_name="MONTHLY_INGEST_STATE_MACHINE_TIMEOUT_SECONDS",
        ),
        endpoint_services=default_interface_endpoint_services(),
        retry=retry,
    )


def _clean_text(value: Any) -> str | None:
    cleaned = str(value or "").strip()
    return cleaned or None


def _positive_int(value: Any, *, default: int, field_name: str) -> int:
    candidate = _clean_text(value)
    if candidate is None:
        return default
    parsed = int(candidate)
    if parsed < 1:
        raise ValueError(f"{field_name} must be at least 1")
    return parsed


def _positive_float(value: Any, *, default: float, field_name: str) -> float:
    candidate = _clean_text(value)
    if candidate is None:
        return default
    parsed = float(candidate)
    if parsed < 1:
        raise ValueError(f"{field_name} must be at least 1")
    return parsed


def _safe_path_segment(value: str | None, *, default: str) -> str:
    candidate = str(value or "").strip().replace("/", "_")
    return candidate or default


def _mapping_or_none(value: Any) -> Mapping[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError("schedule_context must be an object when provided")
    return value


def _coerce_bool(value: Any, *, default: bool, field_name: str) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    candidate = _clean_text(value)
    if candidate is None:
        return default
    normalized = candidate.lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    raise ValueError(f"{field_name} must be a boolean when provided")


__all__ = [
    "DEFAULT_AWS_REGION",
    "DEFAULT_APP_ENV",
    "DEFAULT_ECS_CLUSTER_NAME_REFERENCE",
    "DEFAULT_ECS_TASK_TIMEOUT_SECONDS",
    "DEFAULT_ENDPOINT_POLL_INTERVAL_SECONDS",
    "DEFAULT_ENDPOINT_READY_MAX_ATTEMPTS",
    "DEFAULT_MONTHLY_INGEST_WORKFLOW_BASENAME",
    "DEFAULT_MONTHLY_INGEST_WORKFLOW_VERSION",
    "DEFAULT_STAGING_LAMBDA_TIMEOUT_SECONDS",
    "DEFAULT_STATE_MACHINE_TIMEOUT_SECONDS",
    "ECS_TASK_REQUIRED_ENV_VARS",
    "EcsTaskOutputArtifact",
    "EcsTaskRuntimeContract",
    "MonthlyIngestWorkflowConfig",
    "MonthlyIngestWorkflowInput",
    "STEP_FUNCTION_OPTIONAL_FIELDS",
    "STEP_FUNCTION_INPUT_FIELDS",
    "VpcEndpointServiceConfig",
    "WorkflowRetryConfig",
    "default_ecs_task_log_group_name",
    "default_interface_endpoint_services",
    "default_step_function_log_group_name",
    "load_monthly_ingest_workflow_config",
    "shape_step_function_input",
    "validate_step_function_input_payload",
    "workflow_artifact_index_key",
    "workflow_job_prefix",
    "workflow_manifest_key",
    "workflow_summary_key",
]
