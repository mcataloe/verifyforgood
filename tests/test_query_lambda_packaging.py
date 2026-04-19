from __future__ import annotations

import builtins
import importlib
import sys
from pathlib import Path


def test_lambda_query_import_does_not_require_ingest_package(monkeypatch):
    for module_name in list(sys.modules):
        if module_name == "infrastructure.lambda_query":
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

    module = importlib.import_module("infrastructure.lambda_query")

    assert module.__name__ == "infrastructure.lambda_query"


def test_query_lambda_packaging_includes_private_platform_sources():
    terraform = Path("infrastructure/aws_lambda.tf").read_text(encoding="utf-8")
    script = Path("infrastructure/build_query_package.ps1").read_text(encoding="utf-8")

    assert 'resource "terraform_data" "query_package_build"' in terraform
    assert 'source_dir  = local.query_package_dir' in terraform
    assert "private-platform/src/verification_platform" in terraform
    assert "Copy-Item -Path (Join-Path $repoRoot \"private-platform\\\\src\\\\verification_platform\")" in script
    assert "Copy-Item -Path (Join-Path $moduleDir \"verification_platform\")" in script
    assert "--platform manylinux2014_x86_64" in script
    assert "--python-version 311" in script
    assert "--only-binary=:all:" in script


def test_lambda_query_shim_points_to_backend_runtime_source():
    source = Path("infrastructure/lambda_query.py").read_text(encoding="utf-8")

    assert "Compatibility shim for the backend-owned API runtime" in source
    assert "verification_backend.api" in source

