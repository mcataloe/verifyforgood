from __future__ import annotations

import json
from pathlib import Path


def test_split_plan_has_expected_sections():
    payload = json.loads(Path("split-plan.json").read_text(encoding="utf-8"))
    assert "operational_layers" in payload
    assert "public_repo" in payload
    assert "private_repo" in payload
    assert "infra_repo" in payload
    assert "shared_contracts" in payload
    assert "backend_runtime_targets" in payload
    assert "test_layers" in payload
    assert "dependency_rules" in payload
    assert "migration_sequence" in payload


def test_repo_target_architecture_doc_exists():
    doc = Path("docs/repo-target-architecture.md")
    workspace_doc = Path("docs/architecture/form990-local-workspace-architecture.md")
    assert doc.exists()
    assert workspace_doc.exists()
    text = doc.read_text(encoding="utf-8")
    workspace_text = workspace_doc.read_text(encoding="utf-8")
    assert "All billing stays private-platform" in text
    assert "Backend Runtime Ownership Targets" in text
    assert "`backend/` becomes the executable runtime host layer" in text
    assert "What Should Be Done First" in text
    assert "local-first workspace execution model" in text

    assert "Workspace Contract" in workspace_text
    assert "process one archive at a time inside a workspace" in workspace_text
    assert "32 GiB ECS ephemeral storage" in workspace_text
    assert "verification_backend.ingest_task.orchestration.workspace" in workspace_text

    readiness = Path("docs/backend-stage1-readiness.md")
    assert readiness.exists()
    readiness_text = readiness.read_text(encoding="utf-8")
    assert "Entrypoint Ownership Map" in readiness_text
    assert "Shared Contract Guidance" in readiness_text
    assert "Runtime Extraction Targets" in readiness_text


def test_package_scaffolding_roots_exist():
    backend_root = Path("backend")
    backend_pyproject = backend_root / "pyproject.toml"
    backend_env_example = backend_root / ".env.local.example"
    backend_api = Path("backend/api")
    backend_worker = Path("backend/worker")
    backend_ingest = Path("backend/ingest-task")
    backend_shared = Path("backend/shared")
    backend_tests = backend_root / "tests" / "README.md"
    backend_api_package = backend_api / "src" / "verification_backend" / "api"
    backend_worker_package = backend_worker / "src" / "verification_backend" / "worker"
    backend_ingest_package = backend_ingest / "src" / "verification_backend" / "ingest_task"
    backend_ingest_form990 = backend_ingest_package / "form990"
    backend_ingest_monthly = backend_ingest_package / "monthly"
    backend_ingest_discovery = backend_ingest_package / "discovery"
    backend_ingest_metadata = backend_ingest_package / "metadata"
    backend_ingest_download = backend_ingest_package / "download"
    backend_ingest_extract = backend_ingest_package / "extract"
    backend_ingest_hashing = backend_ingest_package / "hashing"
    backend_ingest_parse = backend_ingest_package / "parse"
    backend_ingest_persist = backend_ingest_package / "persist"
    backend_ingest_cleanup = backend_ingest_package / "cleanup"
    backend_ingest_orchestration = backend_ingest_package / "orchestration"
    backend_ingest_entrypoints = backend_ingest_package / "entrypoints"
    backend_shared_package = backend_shared / "src" / "verification_backend" / "shared"
    public_root = Path("public-core/src/verification")
    private_root = Path("private-platform/src/verification_platform")
    private_pyproject = Path("private-platform/pyproject.toml")
    infrastructure_doc = Path("infrastructure/README.md")
    public_tests = Path("public-core/tests/README.md")
    private_tests = Path("private-platform/tests/README.md")
    root_tests = Path("tests/README.md")

    assert backend_root.exists()
    assert backend_pyproject.exists()
    assert backend_env_example.exists()
    assert (backend_root / "README.md").exists()
    assert backend_tests.exists()
    assert backend_api.exists()
    assert (backend_api / "README.md").exists()
    assert (backend_api / "Dockerfile").exists()
    assert backend_api_package.exists()
    assert (backend_api_package / "__init__.py").exists()
    assert (backend_api_package / "entrypoint.py").exists()
    assert backend_worker.exists()
    assert (backend_worker / "README.md").exists()
    assert (backend_worker / "Dockerfile").exists()
    assert backend_worker_package.exists()
    assert (backend_worker_package / "__init__.py").exists()
    assert (backend_worker_package / "entrypoint.py").exists()
    assert backend_ingest.exists()
    assert (backend_ingest / "README.md").exists()
    assert (backend_ingest / "Dockerfile").exists()
    assert backend_ingest_package.exists()
    assert (backend_ingest_package / "__init__.py").exists()
    assert (backend_ingest_package / "entrypoint.py").exists()
    assert (backend_ingest_package / "cli.py").exists()
    assert backend_ingest_form990.exists()
    assert (backend_ingest_form990 / "__init__.py").exists()
    assert backend_ingest_monthly.exists()
    assert (backend_ingest_monthly / "__init__.py").exists()
    assert (backend_ingest_monthly / "worker.py").exists()
    assert backend_ingest_discovery.exists()
    assert (backend_ingest_discovery / "__init__.py").exists()
    assert backend_ingest_metadata.exists()
    assert (backend_ingest_metadata / "__init__.py").exists()
    assert backend_ingest_download.exists()
    assert (backend_ingest_download / "__init__.py").exists()
    assert backend_ingest_extract.exists()
    assert (backend_ingest_extract / "__init__.py").exists()
    assert backend_ingest_hashing.exists()
    assert (backend_ingest_hashing / "__init__.py").exists()
    assert backend_ingest_parse.exists()
    assert (backend_ingest_parse / "__init__.py").exists()
    assert backend_ingest_persist.exists()
    assert (backend_ingest_persist / "__init__.py").exists()
    assert backend_ingest_cleanup.exists()
    assert (backend_ingest_cleanup / "__init__.py").exists()
    assert backend_ingest_orchestration.exists()
    assert (backend_ingest_orchestration / "__init__.py").exists()
    assert (backend_ingest_orchestration / "workspace.py").exists()
    assert backend_ingest_entrypoints.exists()
    assert (backend_ingest_entrypoints / "__init__.py").exists()
    assert (backend_ingest_package / "persistence.py").exists()
    assert backend_shared.exists()
    assert (backend_shared / "README.md").exists()
    assert backend_shared_package.exists()
    assert (backend_shared_package / "__init__.py").exists()
    assert (backend_shared_package / "runtime_identity.py").exists()
    assert (backend_shared_package / "cli.py").exists()
    assert (backend_shared_package / "local_dev.py").exists()

    assert public_root.exists()
    assert (public_root / "__init__.py").exists()
    assert (public_root / "README.md").exists()

    assert private_pyproject.exists()
    assert private_root.exists()
    assert (private_root / "__init__.py").exists()
    assert (private_root / "README.md").exists()

    assert infrastructure_doc.exists()
    assert public_tests.exists()
    assert private_tests.exists()
    assert root_tests.exists()


def test_package_scaffolding_docs_define_boundaries():
    backend_text = Path("backend/README.md").read_text(encoding="utf-8")
    backend_api_text = Path("backend/api/README.md").read_text(encoding="utf-8")
    backend_worker_text = Path("backend/worker/README.md").read_text(encoding="utf-8")
    backend_ingest_text = Path("backend/ingest-task/README.md").read_text(encoding="utf-8")
    backend_shared_text = Path("backend/shared/README.md").read_text(encoding="utf-8")
    public_text = Path("public-core/src/verification/README.md").read_text(encoding="utf-8")
    private_text = Path("private-platform/src/verification_platform/README.md").read_text(encoding="utf-8")
    infrastructure_text = Path("infrastructure/README.md").read_text(encoding="utf-8")
    tests_text = Path("tests/README.md").read_text(encoding="utf-8")

    assert "future executable runtime host layer" in backend_text
    assert "backend/` may depend on `public-core/` and `private-platform/`" in backend_text
    assert "python -m pip install -e .\\public-core -e .\\private-platform -e .\\backend" in backend_text
    assert "backend/.env.local" in backend_text
    assert "backend/.env.local.example" in backend_text
    assert "PostgreSQL 16" in backend_text
    assert "createdb verification_platform" in backend_text
    assert "python -m verification_backend.shared.local_dev db-upgrade" in backend_text
    assert "python -m verification_backend.shared.local_dev db-upgrade-nonprofit" in backend_text
    assert "python -m verification_backend.shared.local_dev db-reset-nonprofit" in backend_text
    assert "python -m verification_backend.shared.local_dev db-cutover-nonprofit" in backend_text
    assert "python -m verification_backend.shared.local_dev db-current" in backend_text
    assert "python -m verification_backend.api.entrypoint" in backend_text
    assert "python -m verification_backend.worker.entrypoint" in backend_text
    assert "python -m verification_backend.ingest_task.entrypoint" in backend_text
    assert "docker build -f backend/api/Dockerfile ." in backend_text
    assert "docker build -f backend/worker/Dockerfile ." in backend_text
    assert "docker build -f backend/ingest-task/Dockerfile ." in backend_text
    assert "provisionable ECS service slot" in backend_text

    assert "backend/api/src/verification_backend/api/" in backend_api_text
    assert "verification_backend.api.app:app" in backend_api_text
    assert "backend/.env.local" in backend_api_text
    assert "PLATFORM_POSTGRES_URL" in backend_api_text
    assert "PLATFORM_NONPROFIT_POSTGRES_URL" in backend_api_text
    assert "backend/api/Dockerfile" in backend_api_text
    assert "backend/worker/src/verification_backend/worker/" in backend_worker_text
    assert "backend/worker/Dockerfile" in backend_worker_text
    assert "private-subnet ECS service" in backend_worker_text
    assert "backend/ingest-task/src/verification_backend/ingest_task/" in backend_ingest_text
    assert "python -m verification_backend.ingest_task.cli monthly-worker" in backend_ingest_text
    assert "monthly/worker.py" in backend_ingest_text
    assert "backend/ingest-task/Dockerfile" in backend_ingest_text
    assert "ECS task definition invoked by schedules or one-off runs" in backend_ingest_text
    assert "FORM990_WORKSPACE_DIR" in backend_ingest_text
    assert "workspace/" in backend_ingest_text
    assert "orchestration/workspace.py" in backend_ingest_text
    assert "archive download, extraction, parsing, persistence, and cleanup responsibilities" in backend_ingest_text
    assert "backend/shared/src/verification_backend/shared/" in backend_shared_text
    assert "backend/.env.local" in backend_shared_text
    assert "verification_backend.shared.local_dev db-upgrade" in backend_shared_text

    assert "Forbidden contents" in public_text
    assert "Dependency direction" in public_text
    assert "platform billing" in public_text

    assert "Forbidden contents" in private_text
    assert "Dependency direction" in private_text
    assert "may depend on `verification`" in private_text

    assert "Target role" in infrastructure_text
    assert "deployment/config/wiring only" in infrastructure_text
    assert "PLATFORM_NONPROFIT_STORE_BACKEND" in infrastructure_text
    assert "db-cutover-nonprofit" in infrastructure_text

    assert "public-core/tests/" in tests_text
    assert "private-platform/tests/" in tests_text
    assert "compatibility" in tests_text.lower()


def test_backend_workspace_metadata_and_frontend_boundaries_remain_stable():
    backend_pyproject = Path("backend/pyproject.toml").read_text(encoding="utf-8")
    private_pyproject = Path("private-platform/pyproject.toml").read_text(encoding="utf-8")
    frontend_package = Path("frontend/package.json").read_text(encoding="utf-8")
    frontend_workspace = Path("frontend/pnpm-workspace.yaml").read_text(encoding="utf-8")

    assert 'name = "charity-status-backend"' in backend_pyproject
    assert '"verification_backend.api" = "api/src/verification_backend/api"' in backend_pyproject
    assert '"verification_backend.worker" = "worker/src/verification_backend/worker"' in backend_pyproject
    assert '"verification_backend.ingest_task" = "ingest-task/src/verification_backend/ingest_task"' in backend_pyproject
    assert '"verification_backend.ingest_task.form990"' in backend_pyproject
    assert '"verification_backend.ingest_task.monthly"' in backend_pyproject
    assert '"verification_backend.shared" = "shared/src/verification_backend/shared"' in backend_pyproject
    assert 'packages = [' in backend_pyproject
    assert '"verification_backend.ingest_task"' in backend_pyproject

    assert 'name = "charity-status-private-platform"' in private_pyproject
    assert 'package-dir = {"" = "src"}' in private_pyproject

    assert '"name": "verifyforgood-frontend-workspace"' in frontend_package
    assert "docs:" not in frontend_workspace.lower()
    assert "shared/*" in frontend_workspace


def test_backend_local_env_template_and_entrypoints_reference_shared_loader():
    backend_env_example = Path("backend/.env.local.example").read_text(encoding="utf-8")
    api_entrypoint = Path("backend/api/src/verification_backend/api/entrypoint.py").read_text(encoding="utf-8")
    worker_entrypoint = Path("backend/worker/src/verification_backend/worker/entrypoint.py").read_text(encoding="utf-8")
    ingest_entrypoint = Path("backend/ingest-task/src/verification_backend/ingest_task/entrypoint.py").read_text(encoding="utf-8")
    local_dev = Path("backend/shared/src/verification_backend/shared/local_dev.py").read_text(encoding="utf-8")

    assert "PLATFORM_POSTGRES_ENABLED=true" in backend_env_example
    assert "PLATFORM_POSTGRES_URL=postgresql+psycopg://" in backend_env_example
    assert "PLATFORM_NONPROFIT_POSTGRES_URL=postgresql+psycopg://" in backend_env_example
    assert "PLATFORM_NONPROFIT_STORE_BACKEND=postgres" in backend_env_example
    assert "PLATFORM_NONPROFIT_QUERY_BACKEND=postgres" in backend_env_example
    assert "PORTAL_AUTH_TOKEN_SECRET=dev-portal-auth-secret" in backend_env_example
    assert "SUPPORT_TICKET_EMAIL_ENABLED=false ##PLACEHOLDER##" in backend_env_example
    assert "SUPPORT_TICKET_SMTP_APP_PASSWORD=google-app-password ##PLACEHOLDER##" in backend_env_example
    assert "FORM990_WORKSPACE_DIR=./.workspace/form990" in backend_env_example
    assert "FORM990_WORKSPACE_MAX_BYTES=34359738368" in backend_env_example

    assert "load_backend_local_env" in api_entrypoint
    assert "load_backend_local_env" in worker_entrypoint
    assert "load_backend_local_env" in ingest_entrypoint
    assert '"db-current-nonprofit"' in local_dev
    assert '"db-reset-nonprofit"' in local_dev
    assert '"db-cutover-nonprofit"' in local_dev
    assert "from .cli import main as cli_main" in ingest_entrypoint


def test_infrastructure_nonprofit_database_wiring_is_explicit():
    variables_text = Path("infrastructure/variables.tf").read_text(encoding="utf-8")
    api_ecs_text = Path("infrastructure/aws_api_ecs.tf").read_text(encoding="utf-8")
    worker_ecs_text = Path("infrastructure/aws_ecs.tf").read_text(encoding="utf-8")
    tfvars_text = Path("infrastructure/terraform.tfvars.example").read_text(encoding="utf-8")
    shared_tfvars_text = Path("infrastructure/terraform.shared.tfvars.example").read_text(encoding="utf-8")

    assert 'variable "platform_nonprofit_store_backend"' in variables_text
    assert 'variable "platform_nonprofit_postgres_enabled"' in variables_text
    assert 'variable "platform_nonprofit_postgres_secret_arn"' in variables_text
    assert 'variable "platform_nonprofit_postgres_database_name"' in variables_text

    assert "PLATFORM_NONPROFIT_STORE_BACKEND" in api_ecs_text
    assert "ApiTaskNonprofitPostgresSecretRead" in api_ecs_text
    assert "PLATFORM_NONPROFIT_STORE_BACKEND" in worker_ecs_text
    assert "MonthlyIngestNonprofitPostgresSecretRead" in worker_ecs_text
    assert "WorkerTaskNonprofitPostgresSecretRead" in worker_ecs_text

    assert 'platform_nonprofit_store_backend = "postgres"' in tfvars_text
    assert "platform_nonprofit_postgres_enabled = false" in tfvars_text
    assert 'platform_nonprofit_store_backend         = "postgres"' in shared_tfvars_text
    assert "platform_nonprofit_postgres_enabled      = false" in shared_tfvars_text


def test_vscode_launch_config_preserves_node_entry_and_adds_form990_python_profiles():
    launch_text = Path(".vscode/launch.json").read_text(encoding="utf-8")

    assert '"type": "node"' in launch_text
    assert '"name": "Launch Program"' in launch_text
    assert '"name": "Form990 Local Run"' in launch_text
    assert '"module": "ingest_task.cli"' in launch_text
    assert '"name": "Form990 ECS Parity"' in launch_text
    assert '"module": "verification_backend.ingest_task.cli"' in launch_text
    assert '"FORM990_WORKSPACE_DIR": "${workspaceFolder}/backend/ingest-task/.workspace/form990"' in launch_text
    assert '"name": "EO BMF Local Run"' in launch_text
    assert '"name": "EO BMF ECS Parity"' in launch_text
    assert '"EOBMF_WORKSPACE_DIR": "${workspaceFolder}/backend/ingest-task/.workspace/eo_bmf"' in launch_text


def test_split_plan_records_operational_layers_and_backend_targets():
    payload = json.loads(Path("split-plan.json").read_text(encoding="utf-8"))

    layers = payload["operational_layers"]
    assert layers["frontend"]["root"] == "frontend/"
    assert layers["backend"]["root"] == "backend/"
    assert layers["infrastructure"]["root"] == "infrastructure/"
    assert layers["backend"]["subdirectories"] == [
        "backend/api/",
        "backend/worker/",
        "backend/ingest-task/",
        "backend/shared/",
    ]

    targets = payload["backend_runtime_targets"]
    assert targets["public_api"]["target_directory"] == "backend/api/"
    assert targets["profile_refresh_job"]["target_directory"] == "backend/worker/"
    assert targets["eo_ingest_job"]["target_directory"] == "backend/ingest-task/"
    assert targets["monthly_ingest_job"]["target_directory"] == "backend/ingest-task/"
    assert targets["runtime_shared_contracts"]["target_directory"] == "backend/shared/"


def test_split_plan_referenced_paths_exist():
    payload = json.loads(Path("split-plan.json").read_text(encoding="utf-8"))
    include_paths = []
    for section in ("public_repo", "private_repo", "infra_repo"):
        include_paths.extend(payload.get(section, {}).get("include", []))
        include_paths.extend(payload.get(section, {}).get("candidate_modules", []))
        include_paths.extend(payload.get(section, {}).get("mixed_before_extract", []))
        for paths in payload.get(section, {}).get("service_areas", {}).values():
            include_paths.extend(paths)

    include_paths.extend(payload.get("entrypoints", []))
    include_paths.extend(payload.get("shared_contracts", []))
    include_paths.extend(payload.get("highest_risk_refactors", []))
    for layer in payload.get("operational_layers", {}).values():
        if isinstance(layer, dict):
            include_paths.extend(layer.get("subdirectories", []))
    for paths in payload.get("test_layers", {}).values():
        include_paths.extend(paths)
    for entry in payload.get("backend_runtime_targets", {}).values():
        include_paths.extend(entry.get("current_paths", []))
        target_directory = entry.get("target_directory")
        if target_directory:
            include_paths.append(target_directory)

    # Validate concrete paths only; wildcard patterns are validated by convention.
    flattened = []
    for entry in include_paths:
        if isinstance(entry, list):
            flattened.extend(entry)
        else:
            flattened.append(entry)
    concrete = [entry for entry in flattened if "*" not in entry]
    for entry in concrete:
        assert Path(entry).exists(), f"Missing scaffold path: {entry}"


def test_split_plan_keeps_billing_private():
    payload = json.loads(Path("split-plan.json").read_text(encoding="utf-8"))
    public_candidates = payload["public_repo"].get("candidate_modules", [])
    private_candidates = payload["private_repo"].get("candidate_modules", [])
    assert "infrastructure/verification/billing/" not in public_candidates
    assert "infrastructure/verification/billing/" in private_candidates

