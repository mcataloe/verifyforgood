# Repository Split Guide (Phase 11B Scaffold)

This guide defines how to split this monorepo into:

1. public core repository
2. private platform repository
3. infrastructure deployment repository

## Goals

- keep deterministic nonprofit domain logic open and canonical
- isolate deployment/runtime/platform specifics
- preserve current behavior while enabling low-risk extraction

## Public Repository Contents

Primary package scope:

- `charity_status` domain modules (normalization, scoring, policy, evidence, decision, source models)
- query/use-case logic without platform-specific deployment coupling
- deterministic serving/materialization logic
- tests that validate deterministic domain behavior

Scaffold:

- `public-core/pyproject.toml`
- `public-core/README.md`

## Private Platform Repository Contents

- Lambda runtime handlers
- auth context integration adapters
- quota/metering implementations
- proprietary provider integrations
- customer/workflow-specific orchestration

Scaffold:

- `private-platform/README.md`

## Infrastructure Repository Contents

- Terraform modules/stacks
- environment tfvars and deployment scripts
- account/region-specific pipeline wiring

Scaffold:

- `infra-deployment/README.md`

## Practical Migration Steps

1. Copy paths listed in `split-plan.json.public_repo.include` into the public repo.
2. Move lambda entrypoints and `charity_status/platform` into the private platform repo.
3. Move Terraform and environment deployment artifacts into infra repo.
4. In public repo, switch `public-core/pyproject.toml` package discovery to local `src/` after physical move.
5. Repoint private platform imports to consume published public-core package.

## Guardrails

- Do not copy secrets into the public repo.
- Keep policy/scoring/evidence deterministic and test-covered in the public repo.
- Keep provider-specific runtime credentials and account configuration private.
