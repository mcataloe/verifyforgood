from __future__ import annotations

import builtins
import importlib
import sys
from pathlib import Path


def test_backend_api_runtime_import_does_not_require_ingest_package(monkeypatch):
    for module_name in list(sys.modules):
        if module_name == "verification_backend.api.runtime":
            sys.modules.pop(module_name, None)
            continue
        if module_name.startswith("verification_platform.source_connectors"):
            sys.modules.pop(module_name, None)
            continue
        if module_name.startswith("verification.sources"):
            sys.modules.pop(module_name, None)

    original_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "verification.ingest" or str(name).startswith("verification.ingest."):
            raise ModuleNotFoundError("No module named 'verification.ingest'")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    module = importlib.import_module("verification_backend.api.runtime")

    assert module.__name__ == "verification_backend.api.runtime"


def test_backend_api_package_no_longer_injects_infrastructure_path():
    source = Path("backend/api/src/verification_backend/api/__init__.py").read_text(encoding="utf-8")

    assert "INFRASTRUCTURE_SRC" not in source
    assert "CURRENT_COMPATIBILITY_SOURCE" not in source
    assert "handle_api_event" in source


def test_backend_transport_module_replaces_lambda_named_helpers():
    source = Path("backend/api/src/verification_backend/api/transport.py").read_text(encoding="utf-8")

    assert "build_backend_request" in source
    assert "runtime_response_to_http" in source
    assert "build_api_gateway_event" not in source
    assert "lambda_response_to_http" not in source
