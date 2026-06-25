# Master Repo AGENTS.md — LEAP Local Trial Template

Use this single-file template when you want to test LEAP inside one local repository before installing a global AGENTS.md system-wide.

This file intentionally combines two scopes:

1. **Locked Global Section** — reusable LEAP operating behavior copied from the global AGENTS.md template.
2. **Editable Repository Section** — project-specific AGENTS.md content that should be populated from the current repository.

When this file is placed at the root of a repository as `AGENTS.md`, the code assistant should treat the locked global section as global LEAP behavior and the editable repository section as the repository-level AGENTS.md content.

## Local-Trial Editing Rules

- Do not edit the locked global section unless the user explicitly asks to revise LEAP global behavior.
- Do not remove or rename the section boundary markers.
- Populate only the editable repository section during repo onboarding.
- Preserve the overall two-section structure.
- If a rule in the locked global section refers to the repository-level `AGENTS.md`, interpret that as the editable repository section in this same file.
- If a rule in the editable repository section conflicts with the locked global section, prefer the repository section only for project-specific facts, commands, paths, architecture, and source-of-truth documents.
- If a conflict would create security, privacy, data-loss, or integrity risk, stop and ask.

---

<!-- LEAP_MASTER_GLOBAL_SECTION_START: DO NOT EDIT DURING REPO POPULATION -->

# Global AGENTS.md — LEAP Operating Template

## Purpose

Use LEAP as the default operating model for software engineering tasks unless the user, repository, or task-specific prompt says otherwise.

LEAP is a layered, evidence-first execution model for agent-assisted software work. Its purpose is to keep implementation grounded in the existing repository, aligned to project intent, and delivered in small, reviewable units.

This global file defines reusable behavior across repositories. It should not contain project-specific architecture, product rules, business logic, commands, or layer maps. Those belong in the repository-level `AGENTS.md` and project documentation.

---

## Instruction Priority

When working in a repository, follow instructions in this order:

1. System/developer/tool instructions.
2. Explicit user instructions for the current task.
3. Repository-level `AGENTS.md` and closer scoped agent instruction files.
4. This global `AGENTS.md`.
5. Existing source code, tests, documentation, and conventions.

If instructions conflict, follow the more specific and more recent instruction unless it would create security, data-loss, or integrity risk.

---

## Default LEAP Work Pattern

For non-trivial implementation tasks, use this sequence:

1. Understand the task.
2. Perform repository reconnaissance before editing.
3. Identify the relevant layer, subsystem, feature, route, component, service, data model, or workflow.
4. Locate existing patterns and contracts.
5. Make a concise implementation plan.
6. Implement the smallest coherent change.
7. Add or update relevant tests.
8. Run practical validation checks.
9. Summarize changes, validation, risks, and follow-ups.

Do not treat the task as greenfield unless the repository clearly lacks an existing implementation path.

---

## Reconnaissance Expectations

Before editing code, inspect the repository enough to understand:

- Existing project structure.
- Relevant docs and architecture notes.
- Similar implemented features.
- Naming conventions.
- Data contracts and validation patterns.
- Test structure.
- Build, lint, typecheck, and test commands.
- Known TODOs or roadmap notes related to the task.

Prefer evidence from the repository over assumptions.

---

## LEAP Command Shortcuts

When the user invokes a LEAP command, route it to current LEAP Framework behavior instead of responding generically. Use `docs/leap.md` as the lifecycle reference and the current prompt files when available.

| Command | Route and behavior |
| --- | --- |
| `Run LEAP Charter` | Use `prompts/leap-charter-standard.md` to establish or reconcile project direction, source truth, roadmap, baseline assumptions, and implementation posture. |
| `Run LEAP Recon` | Use `prompts/leap-recon-standard.md` to investigate a focused feature, risk, layer, dependency, contract, repo area, or architecture question before implementation planning. |
| `Generate LEAP Prompt` | Use `prompts/leap-prompt-standard.md` only after source truth, repo reality, scope, validation, stop conditions, and execution configuration are clear enough. |
| `Run LEAP Prompt` | Execute or apply an already-approved LEAP Prompt according to its stated scope, constraints, validation, and stop conditions. |
| `Generate LEAP LHS` | Generate a staged LEAP Prompt format only when implementation gravity warrants Build Units; LHS is not a mandatory lifecycle phase. |
| `Run LEAP LHS` | Execute or apply an approved LHS prompt in Build Unit sequence with its validation and stop conditions. |
| `Run LEAP Governance` | Use `prompts/leap-governance-pass-standard.md` for source-truth, framework, prompt-library, adoption, terminology, or docs drift. |
| `Run LEAP Validation` | Verify completed work against scope, tests/checks, docs, acceptance criteria, and stop conditions. |
| `Run LEAP Handoff` | Summarize completed work, unresolved risks, validation status, deviations, and recommended follow-up. |

Default Recon behavior:

1. Use the repository-level `AGENTS.md` first.
2. Inspect the current repository state.
3. Use the current LEAP Recon Standard Operational Prompt from the LEAP framework repository:
   `/prompts/leap-recon-standard.md`
4. Use source-of-truth documents identified by the repository-level `AGENTS.md`.
5. Perform the Recon Baseline Freshness Check using repository AGENTS.md, baseline metadata if present, source-truth docs, and relevant repo reality.
6. Return Recon only.
7. Do not implement code changes.
8. Do not generate the final LEAP implementation prompt unless the user asks after Recon.

LEAP Charter is not required before every Recon. If the baseline is fresh enough, continue Recon. If minor drift exists, continue and disclose the limitation. If material drift exists, ask whether to run Brownfield Charter or LEAP Governance, continue with limited scope, or defer reconciliation. If source-truth conflict would make Recon unsafe or misleading, stop and recommend reconciliation.

If the LEAP standard prompt, `docs/leap.md`, or repository-level `AGENTS.md` cannot be read, stop and explain what source is unavailable.

The user should not need to paste full framework prompt standards when using standard AGENTS.md behavior.

---

## Planning Standard

For meaningful work, produce a short plan before implementation.

A useful plan should identify:

- The likely files or modules to inspect/change.
- The implementation sequence.
- Tests or checks to run.
- Compatibility concerns.
- Documentation updates.
- Stop conditions or decisions that require the user.

Avoid excessive planning for small, obvious changes.

---

## Implementation Standard

When changing code:

- Reuse existing patterns before introducing new ones.
- Keep changes scoped to the requested task.
- Prefer small, reviewable units.
- Preserve backward compatibility unless explicitly told otherwise.
- Do not rename public interfaces without a clear reason.
- Do not introduce new dependencies without justification.
- Do not mix unrelated refactors into feature work.
- Do not duplicate business logic, schemas, or validation rules.
- Prefer clear, boring, maintainable code over clever code.
- Keep behavior deterministic where practical.
- Handle errors explicitly.
- Preserve existing security, privacy, and auditability boundaries.

---

## LEAP Layer Discipline

When a task references a layer, phase, milestone, or subsection:

- Treat that boundary as the implementation scope.
- Do not skip ahead into later layers unless necessary for compatibility.
- Do not silently implement adjacent layers.
- Preserve earlier layer behavior unless the task explicitly revises it.
- Commit or summarize work by the requested layer/subsection boundary when asked.

If the requested layer depends on unfinished prior work, call that out clearly and either:

- implement the minimum safe prerequisite, or
- stop and ask if the dependency changes scope materially.

---

## House Standard Prompt Behavior

When the user provides a House Standard, LHS, LEAP, or Codex implementation prompt:

- Treat it as the task contract.
- Follow the requested model/reasoning/plan-mode assumptions where applicable.
- Reconcile the prompt against the repository before editing.
- Push back if the prompt conflicts with existing architecture, security, data integrity, or documented product intent.
- Prefer staged implementation over broad rewrites.
- Keep changes modular, testable, and documented.

---

## Questions and Stop Conditions

Ask a question before proceeding only when moving forward would create meaningful risk.

Stop and ask before:

- Destructive production-like data changes.
- Dropping or overwriting user data.
- Weakening authentication or authorization.
- Exposing secrets or credentials.
- Adding paid external services.
- Adding major production dependencies.
- Changing public API contracts without migration.
- Replacing major architecture instead of extending it.
- Guessing business rules that materially affect user-facing behavior.
- Implementing a security-sensitive shortcut.
- Committing large unrelated changes.
- Making irreversible git operations.

If the project is explicitly a prototype or POC, destructive changes may be acceptable, but still call out the risk before doing them.

---

## Testing and Validation

After implementation:

- Run the most relevant available tests/checks.
- Prefer targeted tests first, then broader checks when practical.
- Add or update tests when behavior changes.
- Do not claim tests passed if they were not run.
- If tests cannot be run, explain why.
- If tests fail, investigate and report the failure honestly.
- Do not hide known regressions.

Common validation categories:

- Unit tests.
- Integration/API tests.
- Typecheck.
- Lint.
- Build.
- Formatting.
- Migration checks.
- Manual smoke test notes.

Use the repository’s actual commands, not generic commands, whenever possible.

---

## Documentation Standard

Update documentation when a change affects:

- Setup or local development.
- Public behavior.
- User workflows.
- API contracts.
- Data models.
- Environment variables.
- Security assumptions.
- Architecture.
- Layer strategy.
- Operational commands.

Keep docs concise and close to the changed behavior.

---

## Git and Commit Standard

When asked to commit:

- Commit only coherent, reviewable units.
- Use the requested layer/subsection title when provided.
- Do not bundle unrelated work.
- Do not commit generated junk, secrets, local env files, dependency caches, or unrelated formatting churn.
- Check `git status` before committing.
- Include a clear commit message.

Preferred LEAP commit message shape:

`Layer X — Short Descriptive Title`

Examples:

`Layer 6C — Versioning, Review, and Submitted-State Workflow`

`Layer 8A — Integration Provider Contracts`

If the user asks for sequential layer work, complete one subsection, validate it, commit it if requested, then proceed to the next subsection.

---

## Final Response Standard

At completion, summarize:

- What changed.
- Files or areas touched.
- Tests/checks run.
- Any tests/checks not run.
- Risks or follow-ups.
- Whether the work stayed within the requested layer/scope.

Be direct. Do not oversell the result.

---

## Do Not Do

Do not:

- Invent project requirements.
- Fabricate test results.
- Ignore existing docs.
- Replace established architecture without cause.
- Add dependencies casually.
- Hide uncertainty.
- Implement broad refactors under a narrow task.
- Weaken security to make tests pass.
- Commit secrets or `.env` files.
- Treat AI-generated assumptions as source of truth.
- Continue past a serious unresolved ambiguity.


<!-- LEAP_MASTER_GLOBAL_SECTION_END -->

---

<!-- LEAP_MASTER_REPO_SECTION_START: EDIT THIS SECTION ONLY DURING REPO POPULATION -->

# Repository AGENTS.md - VerifyForGood / Charity Status API

## Project Identity

This repository uses LEAP for agent-assisted software delivery. Ground work in the repository's code, tests, docs, migrations, and deployment configuration before implementing changes.

Project name: `Charity Status API` internally, with customer-facing branding configured as `VerifyForGood`.

Project summary: VerifyForGood helps customers verify and monitor U.S. nonprofits using IRS Exempt Organizations data, Form 990 filing data, deterministic scoring/decision logic, selected enrichment sources, organization-scoped billing, and customer portal workflows.

Current maturity:

- Active product/platform codebase, not greenfield.
- Compatibility-first migration from Lambda/API Gateway and infrastructure-heavy runtime ownership toward clearer `frontend/`, `backend/`, `public-core/`, `private-platform/`, and deployment boundaries.
- Primary public API ingress is documented as Route53 -> ALB -> ECS Fargate.
- API Gateway + Lambda remains in Terraform/docs as a deprecated rollback path.
- PostgreSQL/Alembic relational migration is active; older DynamoDB assumptions still appear in docs/tests and must be checked before persistence work.
- Frontend workspace exists for marketing, docs, and authenticated portal surfaces.

Primary users and use cases:

- Customer organizations verify nonprofits by EIN or name, review filings, inspect source/compliance/federal-award views, manage organization settings, use API keys/OAuth client credentials, and manage subscriptions.
- Internal operators/admins manage accounts, billing/control-plane state, migrations, ingest, and deployment operations.

## LEAP Baseline State

| Item | Value |
| --- | --- |
| Baseline record | Inline in `AGENTS.md`; no `leap.baseline.yaml` found |
| Last full reconcile | `Never` |
| Last reconcile mode | `Never` |
| Current source-truth entry point | `README.md` |
| Canonical docs location | `docs/`, plus surface-specific READMEs |
| Archive location | `Not established` |
| Gap register / known drift | `TODO.md` |
| Baseline confidence | `Medium` for repo topology and commands; `Unknown` for formal product-roadmap reconciliation |
| Reconcile triggers | Architecture pivot; persistence/backend cutover; source-truth conflict; stale README/docs; large new phase/layer; public/private repo split; billing/auth contract change |

This AGENTS.md population is not a full Brownfield Charter, Governance pass, or source-truth reconciliation. Do not update this table for ordinary feature work.

Primary source-truth documents:

- `README.md` - main architecture, local development, runtime, deployment, naming, and API context.
- `CUSTOMER_README.md` - customer-facing API surface, workflows, auth, plans, billing, and tenant setup.
- `docs/repo-target-architecture.md` - target split and dependency rules.
- `docs/backend-stage1-readiness.md` - backend runtime ownership and test strategy.
- `docs/repo-split-guide.md` and `split-plan.json` - public/private/infra split planning.
- `docs/architecture/ADR-ecs-runtime-pivot.md` - ECS/ALB API runtime decision.
- `docs/architecture/ADR-platform-persistence-relational-pivot.md` - PostgreSQL migration decision.
- `docs/architecture/ADR-billing-provider.md` - provisional Stripe billing decision.
- `docs/monthly-ingest-architecture.md` and `docs/monthly-ingest-runbook.md` - monthly private-ingest source truth.
- `docs/contributor-naming-rules.md`, `docs/capability-naming-abstraction.md`, and `docs/infrastructure-naming-normalization.md` - naming rules.
- `docs/implementation/` - phase-specific implementation notes and status; verify freshness against code.

Known stale or conflicting documentation risk:

- Some docs still describe DynamoDB materialized profile/cache behavior, while `infrastructure/README.md` says the runtime and Terraform have retired that cache. Verify current code, Terraform, and tests before changing serving/cache behavior.
- Root `tests/` remains the active compatibility suite even though package-local test directories are scaffolded.
- `.gitlab-ci.yml` contains the documented GitLab deployment posture, but many jobs appear commented; verify CI status before relying on automation.

## Repository Layout

- `frontend/` - pnpm workspace for browser applications and shared frontend packages.
- `frontend/marketing/` - public marketing site shell.
- `frontend/portal/` - authenticated customer portal shell.
- `frontend/docs/` - frontend documentation app shell, separate from repository docs.
- `frontend/shared/` - shared frontend API, config, UI, types, and utilities.
- `backend/` - Python backend runtime host workspace.
- `backend/api/` - FastAPI/ASGI API runtime and ECS API image contract.
- `backend/worker/` - scaffolded non-HTTP worker runtime host.
- `backend/ingest-task/` - EO/BMF and Form 990 ECS/local ingest-task runtime.
- `backend/shared/` - backend-local env loading and runtime bootstrap helpers.
- `public-core/` - future public/open-safe package boundary for deterministic nonprofit logic.
- `private-platform/` - private platform package boundary for auth, accounts, billing, admin, runtime, and proprietary orchestration.
- `infrastructure/` - Terraform, deployment wiring, packaging scripts, compatibility shims, and legacy live runtime code still being extracted.
- `infra-deployment/` - scaffold for future deployment-artifacts repository boundary.
- `alembic/` and `alembic.ini` - PostgreSQL schema migrations.
- `tests/` - active integration, compatibility, deployment-adjacent, and legacy monorepo test suite.
- `backend/tests/`, `public-core/tests/`, `private-platform/tests/` - package-local test homes for future or already-isolated coverage.
- `docs/` - architecture, implementation, naming, ingest, and migration documentation.
- `postman/` - Postman collection for API exploration.

## Technology Stack

- Frontend: React 19, TypeScript, Vite, Vitest, ESLint, Prettier, Mantine, Tabler icons, pnpm workspace.
- Backend/API: Python 3.11, FastAPI, Uvicorn, setuptools workspaces, SQLAlchemy, Alembic.
- Domain/runtime code: `charity_status` legacy/internal package, `charity_status_backend`, and `charity_status_platform`.
- Database/persistence: PostgreSQL 16 for local relational development; Amazon RDS for PostgreSQL in infrastructure; transitional/legacy DynamoDB references remain.
- Data/ingest: IRS EO/BMF CSVs, IRS TEOS/Form 990 ZIP/XML data, local/ECS workspaces, S3/Glue/Athena in deployment and older/compatibility paths.
- Infrastructure: Terraform, AWS ECS Fargate, ALB, Route53, ACM, ECR, Lambda rollback shims, EventBridge, Step Functions, S3, CloudWatch, Secrets Manager/SSM-style secret injection.
- Billing/auth integrations: Stripe-hosted Checkout and billing portal; API keys and OAuth client credentials.
- CI/CD: GitLab CI/CD is documented as canonical for backend image build, ECR publish, Terraform plan, and manual rollout; verify actual job enablement in `.gitlab-ci.yml`.
- Package managers: `pip` for Python; `pnpm@10.33.0` for frontend.
- Test frameworks: `pytest` for Python; `vitest` and Testing Library for frontend.
- Runtime versions: Python `>=3.11`; frontend package manager `pnpm@10.33.0`; Terraform examples use `1.9.8` in CI comments.

## Setup and Development Commands

Python/backend setup from the repository root:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r .\infrastructure\requirements.txt -r .\infrastructure\requirements-dev.txt
python -m pip install -e .\public-core -e .\private-platform -e .\backend
```

Frontend setup:

```powershell
cd frontend
pnpm install
```

Local PostgreSQL setup:

```powershell
Copy-Item .\backend\.env.local.example .\backend\.env.local
createdb verification_platform
python -m charity_status_backend.shared.local_dev db-upgrade
python -m charity_status_backend.shared.local_dev db-current
```

Local backend API:

```powershell
python -m charity_status_backend.api.entrypoint
```

Frontend dev servers, run from `frontend/`:

```powershell
pnpm run dev:portal
pnpm run dev:marketing
pnpm run dev:docs
```

Ingest-task local examples:

```powershell
python -m charity_status_backend.ingest_task.cli run --limit 1
python -m charity_status_backend.ingest_task.cli run-eo-bmf
python -m charity_status_backend.ingest_task.cli ecs-run
python -m charity_status_backend.ingest_task.cli monthly-worker
```

Docker build contracts, run from the repository root:

```powershell
docker build -f backend/api/Dockerfile .
docker build -f backend/worker/Dockerfile .
docker build -f backend/ingest-task/Dockerfile .
```

## Validation Commands

Python tests:

```powershell
python -m pytest -q
```

Frontend checks, run from `frontend/`:

```powershell
pnpm run format:check
pnpm run lint
pnpm run test
pnpm run typecheck
pnpm run build
```

Frontend formatting when intentionally changing frontend files:

```powershell
pnpm run format
```

Terraform validation:

```powershell
terraform -chdir=infrastructure init -backend=false
terraform -chdir=infrastructure fmt -check
terraform -chdir=infrastructure validate
```

Migration commands:

```powershell
python -m charity_status_backend.shared.local_dev db-upgrade
python -m charity_status_backend.shared.local_dev db-current
alembic upgrade head
alembic revision -m "describe change"
```

Prefer targeted tests first, then broader checks when practical. Do not claim validation passed unless it was actually run.

## LEAP Project Rules

When a task references a layer, phase, subsection, milestone, or roadmap item:

1. Locate the corresponding docs or TODO section.
2. Confirm current implementation state in code, migrations, tests, and Terraform.
3. Identify affected routes, services, repositories, models, frontend packages, migrations, deployment wiring, and tests.
4. Implement only the requested unit unless a prerequisite is required for safety.
5. Preserve completed prior-layer behavior and existing `/v1/...` contracts.
6. Update relevant tests and docs when behavior, commands, env vars, or contracts change.
7. Summarize remaining gaps and source-truth drift.

During LEAP Recon:

- Start with this repo section, then read `README.md` and the closest relevant README/docs.
- Perform a lightweight baseline freshness check using the table above, `TODO.md`, source docs, code, tests, and deployment evidence.
- If the task touches integrations, API contracts, auth, billing, SDKs, provider boundaries, identity, payments, queues, events, or infrastructure dependencies, inspect package manifests, Terraform, tests, mocks, and provider-facing docs in the repo.
- If `leap.dependencies.yaml` is missing, report that as a limitation, not a blocker.
- Return Recon only unless the user asks for implementation or prompt generation.

LEAP Prompt / implementation handoff expectations:

- Include scope, source-truth docs, files likely to change, validation commands, stop conditions, and compatibility risks.
- Call out whether work is in `frontend`, `backend`, `public-core`, `private-platform`, `infrastructure`, or a compatibility shim.
- For staged work, keep units aligned to documented phases/layers and avoid cross-layer cleanup unless required.

## Project Source of Truth

Use this order of truth when making decisions:

1. Explicit user instruction for the current task.
2. Current repository code, migrations, tests, and Terraform.
3. This `AGENTS.md` repo section and any future closer scoped instruction files.
4. `README.md` and surface-specific READMEs.
5. Architecture ADRs and implementation docs under `docs/`.
6. `CUSTOMER_README.md` for customer-facing API and product behavior.
7. `TODO.md`, `PLAN.md`, and phase notes.
8. Reasonable inference from nearby patterns.

If sources conflict, call out the conflict and prefer the more specific, more recent, and safer evidence.

## Architecture Rules

- Preserve the documented dependency direction: `frontend` uses HTTP/shared frontend packages only; `backend` may depend on `public-core` and `private-platform`; `private-platform` may depend on `public-core`; `public-core` must not depend on `private-platform`; `infrastructure` may package/deploy runtime entrypoints but application code should not depend on deployment-only modules.
- Keep deterministic, reusable, open-safe nonprofit logic in or moving toward `public-core`.
- Keep auth, customer accounts, billing, quotas, admin operations, proprietary adapters, and runtime orchestration in `private-platform`.
- Keep executable API, worker, ingest-task, and runtime bootstrap concerns in `backend`.
- Keep Terraform, env files, deployment scripts, packaging, and temporary shims in `infrastructure`.
- Treat `infrastructure/lambda_query.py` and other `infrastructure/lambda_*.py` files as compatibility/rollback surfaces unless current code proves otherwise.
- Use service/adapter splits where available: service modules own rules and orchestration; adapter modules own AWS/provider clients and persistence/query execution.
- Do not introduce billing, Stripe, quota, entitlement, or customer-account logic into `public-core`.
- Preserve existing `/v1/...` API routes, auth header behavior, CORS behavior, webhooks, and response envelopes unless a breaking contract change is explicitly approved.
- Follow naming rules: customer-facing product naming can use VerifyForGood; new internal modules/workflows should prefer capability-oriented names; legacy `CharityStatusAPI`, `charity_status`, and deployed resource names should be preserved where compatibility requires.

## Data and Migration Rules

- Inspect SQLAlchemy models, Alembic migrations, store/repository protocols, and cutover docs before changing persistence.
- Use Alembic for PostgreSQL schema evolution.
- Preserve existing data unless a destructive change is explicitly approved.
- Keep migrations additive/reversible where practical and document rollback limits.
- Use `backend/.env.local` for backend local development; do not commit real `.env` files or secret tfvars.
- Treat `PLATFORM_POSTGRES_URL` as the primary local database setting.
- Verify current persistence selectors before changing runtime behavior, including `PLATFORM_POSTGRES_ENABLED`, `PLATFORM_IDENTITY_STORE_BACKEND`, `PLATFORM_NONPROFIT_STORE_BACKEND`, and `PLATFORM_NONPROFIT_QUERY_BACKEND`.
- Do not retire DynamoDB, Lambda, API Gateway, S3/Athena, or compatibility paths based only on stale docs; confirm current code, Terraform, tests, and rollout status.
- Form 990 and EO/BMF local/ECS ingest paths use workspace-local artifacts and PostgreSQL-backed persistence in current backend docs; preserve cleanup and bounded workspace behavior.

## API and Contract Rules

- Keep customer-facing contracts in `CUSTOMER_README.md`, `frontend/shared/api`, route constants, backend routes, and tests aligned.
- All frontend backend calls should flow through `@charity-status/shared-api`.
- Update shared frontend types/config/API helpers together when route behavior changes.
- Stripe-specific behavior belongs behind backend billing services/adapters, not in frontend browser code or generic handlers.
- Admin routes under `/v1/admin/...` are not part of the standard customer API surface.
- Preserve organization-scoped billing and tenant context unless an approved product decision changes it.

## UI/UX Rules

- Follow `frontend/README.md` and package-local patterns.
- Reuse `@charity-status/shared-ui` design tokens, Mantine theme mapping, layout primitives, feedback states, entity-detail, table, and onboarding patterns before adding app-local variants.
- Marketing and docs are public surfaces; portal is protected except for its sign-in boundary.
- `marketing` must not depend on `portal`; `portal` must not depend on `marketing`; both may depend on `shared/*`.
- Portal layouts should stay calm, data-heavy, accessible, and explicit about loading, empty, error, and success states.
- Keep light and dark themes token-driven.
- Local browser runtime config should stay per app; `marketing/.env.example` and `portal/.env.example` document local API assumptions.

## AI / Automation Rules

- The product uses deterministic rules-based scoring today; README states no black-box ML.
- Do not introduce AI-generated or opaque decisioning into verification/scoring without explicit approval and traceability requirements.
- Keep verification, scoring, and billing decisions explainable and auditable.
- Do not fabricate nonprofit facts, customer facts, filings, credentials, billing state, or compliance outcomes.

## Security, Secrets, and Privacy Rules

- Never commit secrets, tokens, credentials, private keys, real `.env` files, or `terraform-*.secrets.tfvars`.
- Use tracked `.example` files for onboarding and local templates.
- Do not weaken API-key auth, OAuth client credentials, portal auth, tenant authorization, billing enforcement, CORS, or webhook verification.
- Keep sensitive runtime values out of plaintext Terraform where secret reference maps are available, such as `api_ecs_secret_arns` and `worker_ecs_secret_arns`.
- Do not collect or store card details directly; Stripe-hosted flows are the documented payment path.
- Avoid logging credentials, payment secrets, raw webhook secrets, or unnecessary customer/tenant data.
- Preserve auditability for identity, organization, billing, admin, and nonprofit access workflows.

## Testing Expectations

When behavior changes:

- Add or update tests close to the changed behavior.
- Use root `tests/` for live integration, compatibility, deployment-adjacent, and mixed-surface coverage while imports still depend on `infrastructure/`.
- Use `public-core/tests/` for deterministic public-core unit tests once code lives there.
- Use `private-platform/tests/` for private service-area and runtime-boundary tests when imports are isolated.
- Use `backend/tests/` for backend runtime bootstrap and entrypoint tests once runtime behavior is isolated.
- Use frontend package-local `src/**/*.test.ts` or `src/**/*.test.tsx` for frontend behavior.
- Do not delete root compatibility tests until live handler imports and deployment wiring no longer need the legacy paths.

Testing priorities:

1. API/contract and response-envelope tests.
2. Persistence/repository and migration tests.
3. Service/domain logic tests.
4. Auth, tenant, billing, and entitlement tests.
5. Frontend route/API-client and UI behavior tests.
6. Terraform/deployment packaging checks.

## Documentation Expectations

Update docs when changes affect product behavior, customer workflows, API contracts, data models, setup commands, environment variables, architecture boundaries, deployment, layer status, or roadmap assumptions.

Keep these docs aligned with relevant changes:

- `README.md`
- `CUSTOMER_README.md`
- `frontend/README.md`
- `backend/README.md`
- `infrastructure/README.md`
- `docs/repo-target-architecture.md`
- `docs/backend-stage1-readiness.md`
- `docs/monthly-ingest-architecture.md`
- `docs/monthly-ingest-runbook.md`
- `docs/architecture/*.md`
- `docs/implementation/*.md`
- `TODO.md` when a documented gap is closed or materially changed

Do not create new strategy, baseline, or roadmap docs unless explicitly asked.

## Commit, Branch, PR, and CI Expectations

- Check `git status` before committing.
- Keep commits scoped to one coherent LEAP unit or documented phase.
- Use the layer/subsection name in commit messages when provided.
- Do not combine unrelated frontend, backend, infrastructure, and docs changes unless the task requires a vertical slice.
- Do not commit generated junk, dependency caches, secrets, local env files, or secret tfvars.
- GitLab CI/CD is the documented deployment path; manual dev rollout is documented for the default branch and prod rollout for tags, but verify `.gitlab-ci.yml` job enablement before relying on it.
- CI image tags are documented as immutable commit-SHA tags rather than `latest`.

TBD: Project owner should confirm branch naming, PR review, required approvals, and whether LEAP commit message format should be mandatory.

Preferred LEAP commit message when no more specific convention is provided:

`Layer/Phase - Short Descriptive Title`

## Stop Conditions

Stop and ask before:

- Destructive PostgreSQL, DynamoDB, S3, or workspace data changes.
- Changing auth/session/API-key/OAuth/tenant/organization ownership rules.
- Changing billing provider behavior, Stripe webhook semantics, subscription state, entitlement enforcement, trial behavior, overage policy, or payment flows.
- Breaking public `/v1/...` contracts, customer docs, frontend shared API contracts, or webhook contracts.
- Retiring API Gateway/Lambda rollback resources, DynamoDB paths, or compatibility shims without explicit rollout approval.
- Adding paid external services, live provider integrations, or new production dependencies.
- Changing Terraform state backends, production tfvars, Route53, ACM, ALB, ECS, RDS, or secret wiring.
- Replacing the documented architecture instead of extending it incrementally.
- Implementing unclear business rules for nonprofit eligibility, scoring, compliance, billing, tenant access, or admin operations.
- Weakening privacy, traceability, auditability, CORS, auth, or webhook security.

## Completion Requirements

A task is complete when:

- The requested behavior or recon output is delivered within the requested LEAP scope.
- The change follows existing repo boundaries and naming rules.
- Relevant tests/checks were run or explicitly not run with reason.
- Docs were updated when commands, contracts, env vars, architecture, or user workflows changed.
- Known source-truth drift, compatibility risks, and follow-ups are called out.
- The final response identifies files/areas changed, validation, tests not run, risks, and whether the work stayed within scope.

<!-- LEAP_MASTER_REPO_SECTION_END -->
