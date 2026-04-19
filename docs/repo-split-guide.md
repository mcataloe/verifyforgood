# Repository Split Guide

This guide defines the intended operational layering and package/code boundaries.

Operational layers:

1. `frontend/`
2. `backend/`
3. `infrastructure/`

Code/package boundaries:

1. `public-core/`
2. `private-platform/`

The detailed current-state assessment and target-state map live in:

- `docs/repo-target-architecture.md`

## Current Direction

- `frontend/` is the dedicated browser/runtime UI layer and should remain isolated from Python runtime internals.
- `backend/` is the future executable runtime host layer for the API server, workers, ingest tasks, and runtime-shared bootstrap concerns.
- `public-core/` is for deterministic nonprofit/domain logic only.
- `private-platform/` is for all platform behavior, including auth, control-plane, operator workflows, runtime composition, proprietary adapters, and all billing.
- `infrastructure/` is for deployment/config/wiring only.

Important clarification:

- `backend/` is not a replacement for `public-core/` or `private-platform/`.
- `backend/` hosts runnable processes and composition roots.
- `public-core/` and `private-platform/` remain the reusable package boundaries underneath those runtimes.

## Key Boundary Rules

- `frontend/` must not import Python runtime code from `backend/`, `private-platform/`, or `infrastructure/`
- `backend/` may depend on `public-core/` and `private-platform/`
- `verification_platform` may depend on `verification`
- `verification` must not depend on `verification_platform`
- `private-platform/` must not depend on `backend/` or `infrastructure/`
- `infrastructure/` should package and deploy backend entrypoints, not contain business logic

Billing rule:

- billing is private-platform only
- public-core must not own subscription, plan, quota, entitlement, Stripe, or customer billing workflow logic

## Practical Migration Guidance

1. Lock the `backend/` topology, ownership docs, and compatibility metadata first.
2. Fix boundary violations before moving code.
3. Introduce backend-shared runtime wrappers and compatibility exports before moving live handlers.
4. Extract low-risk deterministic public-core packages first.
5. Move backend runtime hosts out of `infrastructure/` incrementally.
6. Reduce `infrastructure/` to Terraform, env config, deployment scripts, and temporary shims last.

## Guardrails

- Do not copy secrets into public artifacts.
- Keep public-core open-safe and deployment-agnostic.
- Keep AWS, Stripe, env parsing, and operator workflows private.
- Avoid moving runtime entrypoints and refactoring mixed modules in the same change.
- Treat `backend/` as the executable runtime layer only; do not collapse frontend and backend into a single workspace/toolchain.

