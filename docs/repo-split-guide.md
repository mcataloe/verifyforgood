# Repository Split Guide

This guide defines the intended split between:

1. `public-core/`
2. `private-platform/`
3. `infrastructure/`

The detailed current-state assessment and target-state map live in:

- `docs/repo-target-architecture.md`

## Current Direction

- `public-core/` is for deterministic nonprofit/domain logic only.
- `private-platform/` is for all platform behavior, including auth, control-plane, operator workflows, runtime composition, proprietary adapters, and all billing.
- `infrastructure/` is for deployment/config/wiring only.

## Key Boundary Rules

- `charity_status_platform` may depend on `charity_status`
- `charity_status` must not depend on `charity_status_platform`
- `infrastructure/` should deploy packaged entrypoints, not contain business logic

Billing rule:

- billing is private-platform only
- public-core must not own subscription, plan, quota, entitlement, Stripe, or customer billing workflow logic

## Practical Migration Guidance

1. Fix boundary violations before moving code.
2. Extract low-risk deterministic public-core packages first.
3. Move private-platform orchestration and adapters after seam fixes land.
4. Reduce `infrastructure/` to Terraform, env config, deployment scripts, and temporary shims last.

## Guardrails

- Do not copy secrets into public artifacts.
- Keep public-core open-safe and deployment-agnostic.
- Keep AWS, Stripe, env parsing, and operator workflows private.
- Avoid moving runtime entrypoints and refactoring mixed modules in the same change.
