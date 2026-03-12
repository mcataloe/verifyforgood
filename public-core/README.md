# Charity Status Public Core (Scaffold)

This directory is split scaffolding for the future public repository.

In this monorepo phase, the canonical source still lives in:

- `infrastructure/charity_status/`

The `pyproject.toml` here is intentionally configured to package `charity_status` from that location so contributors can validate packaging boundaries before a physical repo split.

## Intended Public-Core Scope

- deterministic normalization
- query/domain mapping
- scoring
- decisioning
- policy engine
- evidence generation
- enrichment abstractions and normalized source models
- serving/materialization domain logic (without deployment-specific wiring)

## Out of Scope for Public-Core

- Terraform
- AWS Lambda runtime handlers
- API Gateway wiring
- account/environment-specific secrets and deployment config

See `docs/repo-split-guide.md` and `split-plan.json` at repository root for migration details.
