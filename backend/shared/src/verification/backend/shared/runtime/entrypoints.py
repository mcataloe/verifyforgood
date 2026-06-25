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
        current_module="verification.backend.customer.api.runtime",
        current_handler="handle_api_event",
        target_service_area="runtime",
        runtime_kind="api_handler",
        notes=(
            "Canonical API runtime ownership lives under backend/customer-api.",
            "The ECS/ALB HTTP transport dispatches directly into the backend runtime request seam.",
        ),
    ),
    BackendEntrypoint(
        surface="profile_refresh_job",
        current_module="verification.backend.worker.entrypoint",
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
        current_module="verification.backend.ingest.federal.eo_bmf_ecs_runtime",
        current_handler="main",
        target_service_area="runtime",
        runtime_kind="job_handler",
        notes=(
            "Canonical EO/BMF ingest ownership lives under backend/ingest/federal.",
            "The ECS-style runtime executes directly from the federal ingest package without infrastructure shims.",
        ),
    ),
    BackendEntrypoint(
        surface="monthly_ingest_job",
        current_module="verification.backend.ingest.federal.monthly.worker",
        current_handler="main",
        target_service_area="runtime",
        runtime_kind="job_handler",
        notes=(
            "Canonical Form 990 monthly ingest ownership lives under backend/ingest/federal.",
            "Uses the workspace-plus-PostgreSQL runtime directly from the federal ingest package.",
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
