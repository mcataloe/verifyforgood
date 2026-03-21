from __future__ import annotations

import builtins
import importlib
import sys


def test_lambda_query_import_does_not_require_ingest_package(monkeypatch):
    for module_name in list(sys.modules):
        if module_name == "infrastructure.lambda_query":
            sys.modules.pop(module_name, None)
            continue
        if module_name.startswith("verification_platform.source_connectors"):
            sys.modules.pop(module_name, None)
            continue
        if module_name.startswith("charity_status.sources"):
            sys.modules.pop(module_name, None)

    original_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "charity_status.ingest" or str(name).startswith("charity_status.ingest."):
            raise ModuleNotFoundError("No module named 'charity_status.ingest'")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    module = importlib.import_module("infrastructure.lambda_query")

    assert module.__name__ == "infrastructure.lambda_query"
