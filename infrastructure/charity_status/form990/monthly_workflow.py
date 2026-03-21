from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from charity_status.form990.storage import raw_source_key
from charity_status.ingest.workflow import (
    EcsTaskRuntimeContract,
    MonthlyIngestWorkflowConfig,
    MonthlyIngestWorkflowInput,
    load_monthly_ingest_workflow_config,
    shape_step_function_input,
)


@dataclass(frozen=True)
class Form990MonthlyWorkflowBinding:
    bucket: str
    raw_source_prefix: str
    manifest_prefix: str
    source_download_timeout_seconds: int
    workflow: MonthlyIngestWorkflowConfig
    ecs_contract: EcsTaskRuntimeContract = field(default_factory=EcsTaskRuntimeContract)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not str(self.bucket or "").strip():
            errors.append("BUCKET is required")
        if not str(self.raw_source_prefix or "").strip():
            errors.append("FORM990_RAW_SOURCE_PREFIX is required")
        if not str(self.manifest_prefix or "").strip():
            errors.append("FORM990_MANIFEST_PREFIX is required")
        if int(self.source_download_timeout_seconds) < 1:
            errors.append("FORM990_SOURCE_DOWNLOAD_TIMEOUT_SECONDS must be at least 1")
        errors.extend(self.workflow.validate())
        return errors

    def build_staged_source_key(
        self,
        *,
        source_year: str,
        source_kind: str,
        source_archive_key: str,
        source_signature: str,
        source_filename: str,
    ) -> str:
        return raw_source_key(
            self.raw_source_prefix,
            source_year,
            source_kind,
            source_archive_key,
            source_signature,
            source_filename,
        )

    def build_downloaded_source_step_function_input(
        self,
        *,
        source_year: str,
        source_kind: str,
        source_archive_key: str,
        source_signature: str,
        source_filename: str,
        job_id: str,
        correlation_id: str | None = None,
    ) -> MonthlyIngestWorkflowInput:
        source_key = self.build_staged_source_key(
            source_year=source_year,
            source_kind=source_kind,
            source_archive_key=source_archive_key,
            source_signature=source_signature,
            source_filename=source_filename,
        )
        return shape_step_function_input(
            source_bucket=self.bucket,
            source_key=source_key,
            destination_bucket=self.bucket,
            destination_prefix=self.manifest_prefix,
            job_id=job_id,
            correlation_id=correlation_id,
            workflow_version=self.workflow.workflow_version,
        )

    def build_ecs_environment(self, workflow_input: MonthlyIngestWorkflowInput | Mapping[str, str]) -> dict[str, str]:
        return self.ecs_contract.build_environment(
            workflow_input,
            workflow_name=self.workflow.workflow_name,
        )


def load_form990_monthly_workflow_binding(env: Mapping[str, str] | None = None) -> Form990MonthlyWorkflowBinding:
    source = env or {}
    return Form990MonthlyWorkflowBinding(
        bucket=str(source.get("BUCKET") or "").strip(),
        raw_source_prefix=str(source.get("FORM990_RAW_SOURCE_PREFIX") or "form990/raw-sources/").strip(),
        manifest_prefix=str(source.get("FORM990_MANIFEST_PREFIX") or "form990/normalized/manifests/").strip(),
        source_download_timeout_seconds=int(source.get("FORM990_SOURCE_DOWNLOAD_TIMEOUT_SECONDS") or "300"),
        workflow=load_monthly_ingest_workflow_config(source),
    )


# TODO: Later phases can add workflow-specific schedule builders on top of this binding.
# TODO: Later phases can add workflow-specific ECS artifact/result interpretation helpers.


__all__ = [
    "Form990MonthlyWorkflowBinding",
    "load_form990_monthly_workflow_binding",
]
