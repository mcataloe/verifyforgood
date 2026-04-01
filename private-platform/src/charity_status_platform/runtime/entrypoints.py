from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BackendEntrypoint:
    surface: str
    current_module: str
    current_handler: str
    target_service_area: str
    runtime_kind: str
    notes: tuple[str, ...] = ()

    @property
    def import_path(self) -> str:
        return f"{self.current_module}.{self.current_handler}"


ENTRYPOINTS = (
    BackendEntrypoint(
        surface="public_api",
        current_module="infrastructure.lambda_query",
        current_handler="handler",
        target_service_area="runtime",
        runtime_kind="api_handler",
        notes=(
            "Retained as the rollback Lambda handler import path for the public, customer, admin, and webhook HTTP API surface.",
            "Canonical API runtime ownership now lives under backend/api while this path remains a thin compatibility adapter.",
        ),
    ),
    BackendEntrypoint(
        surface="profile_refresh_job",
        current_module="infrastructure.lambda_refresh",
        current_handler="handler",
        target_service_area="runtime",
        runtime_kind="job_handler",
        notes=(
            "Coordinates materialized-profile refresh behavior.",
            "Depends on runtime adapter assembly rather than customer-facing transport contracts.",
        ),
    ),
    BackendEntrypoint(
        surface="eo_ingest_job",
        current_module="infrastructure.lambda_ingest",
        current_handler="handler",
        target_service_area="runtime",
        runtime_kind="job_handler",
        notes=("Downloads and persists EO/BMF source files.",),
    ),
    BackendEntrypoint(
        surface="form990_ingest_job",
        current_module="infrastructure.lambda_form990",
        current_handler="handler",
        target_service_area="runtime",
        runtime_kind="job_handler",
        notes=(
            "Acts as the primary Form 990 ingest entrypoint.",
            "Still owns both direct-ingest compatibility and discovery/orchestration branching.",
        ),
    ),
    BackendEntrypoint(
        surface="form990_orchestrator",
        current_module="infrastructure.lambda_form990_orchestrator",
        current_handler="handler",
        target_service_area="runtime",
        runtime_kind="worker_shim",
        notes=("Currently remains a thin compatibility shim over the main Form 990 handler.",),
    ),
    BackendEntrypoint(
        surface="form990_worker",
        current_module="infrastructure.lambda_form990_worker",
        current_handler="handler",
        target_service_area="runtime",
        runtime_kind="worker_handler",
        notes=("Processes queued Form 990 source-download, source-batch, and filing chunks.",),
    ),
)


def entrypoint_by_surface(surface: str) -> BackendEntrypoint:
    normalized = str(surface or "").strip().lower()
    for entrypoint in ENTRYPOINTS:
        if entrypoint.surface == normalized:
            return entrypoint
    raise KeyError(f"Unknown backend entrypoint surface: {surface}")


__all__ = ["BackendEntrypoint", "ENTRYPOINTS", "entrypoint_by_surface"]
