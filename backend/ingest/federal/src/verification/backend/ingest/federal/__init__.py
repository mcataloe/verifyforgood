"""Backend-owned federal ingest runtime package."""

RUNTIME_NAME = "federal-ingest"
CANONICAL_LOCAL_ENTRYPOINT = "python -m verification.backend.ingest.federal.cli monthly-worker"

FORM990_WORKSPACE_MODULES = (
    "verification.backend.ingest.federal.discovery",
    "verification.backend.ingest.federal.metadata",
    "verification.backend.ingest.federal.download",
    "verification.backend.ingest.federal.extract",
    "verification.backend.ingest.federal.hashing",
    "verification.backend.ingest.federal.parse",
    "verification.backend.ingest.federal.persist",
    "verification.backend.ingest.federal.cleanup",
    "verification.backend.ingest.federal.orchestration",
)

__all__ = [
    "RUNTIME_NAME",
    "CANONICAL_LOCAL_ENTRYPOINT",
    "FORM990_WORKSPACE_MODULES",
]
