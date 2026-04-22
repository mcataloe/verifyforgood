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
        current_module="verification_backend.api.runtime",
        current_handler="handle_api_event",
        target_service_area="runtime",
        runtime_kind="api_handler",
        notes=(
            "Canonical API runtime ownership lives under backend/api.",
            "The ECS/ALB HTTP transport dispatches directly into the backend runtime request seam.",
        ),
    ),
    BackendEntrypoint(
        surface="profile_refresh_job",
        current_module="verification_backend.worker.entrypoint",
        current_handler="main",
        target_service_area="runtime",
        runtime_kind="job_handler",
        notes=(
            "Refresh is retired and backend/worker remains a neutral scaffold.",
            "This surface is retained only as an ownership map entry for future worker responsibilities.",
        ),
    ),
    BackendEntrypoint(
        surface="eo_ingest_job",
        current_module="infrastructure.eo_bmf_ingest_worker",
        current_handler="handler",
        target_service_area="runtime",
        runtime_kind="job_handler",
        notes=(
            "Acts as the backend-owned EO/BMF ingest compatibility shim.",
            "Routes to the local/ECS-style workspace-plus-PostgreSQL runtime under backend/ingest-task.",
        ),
    ),
    BackendEntrypoint(
        surface="monthly_ingest_job",
        current_module="infrastructure.monthly_ingest_worker",
        current_handler="main",
        target_service_area="runtime",
        runtime_kind="job_handler",
        notes=(
            "Acts as the canonical backend-owned Form 990 monthly ingest entrypoint.",
            "Uses the workspace-plus-PostgreSQL runtime rather than the retired Lambda/S3 orchestration path.",
        ),
    ),
)


def entrypoint_by_surface(surface: str) -> BackendEntrypoint:
    normalized = str(surface or "").strip().lower()
    for entrypoint in ENTRYPOINTS:
        if entrypoint.surface == normalized:
            return entrypoint
    raise KeyError(f"Unknown backend entrypoint surface: {surface}")


__all__ = ["BackendEntrypoint", "ENTRYPOINTS", "entrypoint_by_surface"]
