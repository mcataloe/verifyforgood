# Charity Status Public Core (Scaffold)

This directory is split scaffolding for the future public repository.

In this monorepo phase, the canonical source still lives in:

- `infrastructure/verification/`

The `pyproject.toml` here is intentionally configured to package `verification` from that location so contributors can validate packaging boundaries before a physical repo split.
The package now has an active `src/` root for the first extracted open-safe modules while the live application runtime still imports from `infrastructure/verification/`.

Target package root after extraction:

- `public-core/src/verification/`

Scaffolding added in this repo phase:

- `public-core/src/verification/__init__.py`
- `public-core/src/verification/README.md`

Officially extracted modules in this phase:

- `verification.normalization`
- `verification.sources`
- schema-only `verification.evidence`
- schema-only `verification.policy`

Compatibility note:

- existing server/runtime imports are unchanged
- `infrastructure/verification/` remains the live application path for now
- extracted modules are copied into `public-core/src/verification/` first so future phases can flip imports safely

## Intended Public-Core Scope

- deterministic normalization
- query/domain mapping
- scoring
- decisioning
- policy engine
- evidence generation
- enrichment abstractions and normalized source models
- serving/materialization domain logic (without deployment-specific wiring)
- Form 990 parsing and deterministic transformation logic

Public-core boundary rule:

- no platform billing lives here
- no Stripe, subscription, quota, entitlement, or customer billing workflow logic belongs in public-core

## Out of Scope for Public-Core

- Terraform
- AWS Lambda runtime handlers
- API Gateway wiring
- account/environment-specific secrets and deployment config
- platform auth and control-plane orchestration
- AWS/Stripe adapters
- all platform billing

See `docs/repo-target-architecture.md`, `docs/repo-split-guide.md`, and `split-plan.json` at repository root for migration details.

