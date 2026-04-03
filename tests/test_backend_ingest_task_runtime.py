from __future__ import annotations

import importlib
import sys


def test_infrastructure_form990_lambda_is_backend_owned_shim():
    sys.modules.pop("infrastructure.lambda_form990", None)
    module = importlib.import_module("infrastructure.lambda_form990")

    assert "backend\\ingest-task\\src\\charity_status_backend\\ingest_task\\form990\\runtime.py" in module.__file__


def test_infrastructure_form990_worker_is_backend_owned_shim():
    sys.modules.pop("infrastructure.lambda_form990_worker", None)
    module = importlib.import_module("infrastructure.lambda_form990_worker")

    assert "backend\\ingest-task\\src\\charity_status_backend\\ingest_task\\form990\\worker.py" in module.__file__


def test_infrastructure_nonprofit_ingest_persistence_is_backend_owned_shim():
    sys.modules.pop("infrastructure.nonprofit_ingest_persistence", None)
    module = importlib.import_module("infrastructure.nonprofit_ingest_persistence")

    assert "infrastructure\\nonprofit_ingest_persistence.py" in module.__file__
    assert module.build_form990_nonprofit_persistence_service.__module__ == "charity_status_backend.ingest_task.persistence.nonprofit_persistence"


def test_infrastructure_monthly_worker_wrapper_calls_backend_cli():
    sys.modules.pop("infrastructure.monthly_ingest_worker", None)
    module = importlib.import_module("infrastructure.monthly_ingest_worker")

    assert module.main.__module__ == "charity_status_backend.ingest_task.monthly.worker"


def test_backend_ingest_task_exports_local_entrypoint_metadata():
    package = importlib.import_module("charity_status_backend.ingest_task")

    assert package.RUNTIME_NAME == "ingest_task"
    assert "infrastructure.lambda_form990.handler" in package.CURRENT_COMPATIBILITY_SOURCES
    assert package.CANONICAL_LOCAL_ENTRYPOINT == "python -m charity_status_backend.ingest_task.cli.monthly_ingest_task"


def test_ingest_task_cli_alias_calls_backend_cli():
    sys.modules.pop("ingest_task.cli", None)
    module = importlib.import_module("ingest_task.cli")

    assert module.main.__module__ == "ingest_task.cli"
