from __future__ import annotations

import importlib


def test_backend_federal_ingest_exports_runtime_metadata():
    package = importlib.import_module("verification.backend.ingest.federal")

    assert package.RUNTIME_NAME == "federal-ingest"
    assert (
        package.CANONICAL_LOCAL_ENTRYPOINT
        == "python -m verification.backend.ingest.federal.cli monthly-worker"
    )
    assert "verification.backend.ingest.federal.orchestration" in package.FORM990_WORKSPACE_MODULES


def test_backend_federal_ingest_runtime_entrypoints_are_backend_owned():
    entrypoint = importlib.import_module("verification.backend.ingest.federal.entrypoint")
    cli = importlib.import_module("verification.backend.ingest.federal.cli")
    eo_bmf = importlib.import_module("verification.backend.ingest.federal.eo_bmf_ecs_runtime")
    monthly = importlib.import_module("verification.backend.ingest.federal.monthly.worker")
    persistence = importlib.import_module("verification.backend.ingest.federal.persistence")

    assert entrypoint.main.__module__ == "verification.backend.ingest.federal.entrypoint"
    assert cli.main.__module__ == "verification.backend.ingest.federal.cli"
    assert eo_bmf.main.__module__ == "verification.backend.ingest.federal.eo_bmf_ecs_runtime"
    assert monthly.main.__module__ == "verification.backend.ingest.federal.monthly.worker"
    assert (
        persistence.build_form990_nonprofit_persistence_service.__module__
        == "verification.backend.ingest.federal.persistence.nonprofit_persistence"
    )
