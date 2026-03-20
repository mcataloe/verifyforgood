# `charity_status` Public-Core Package Root

Purpose:

- future canonical package root for reusable open-safe domain logic
- stable home for deterministic nonprofit verification, scoring, policy, normalization, serving-domain, state-registry, and Form 990 transformation logic

Allowed contents:

- deterministic domain models and services
- pure use-case orchestration
- interfaces or ports needed by reusable logic
- parser and transformation code that does not require platform secrets or deployment-specific runtime wiring

Forbidden contents:

- platform billing
- Stripe integration
- auth credential stores and customer account lifecycle orchestration
- AWS SDK adapters
- environment-specific configuration parsing
- Lambda handler and API Gateway transport wiring

Dependency direction:

- `charity_status` must not depend on `charity_status_platform`
- `charity_status` must not depend on deployment-only code under `infrastructure/`

Current monorepo note:

- this directory is scaffolding only in the current phase
- the live implementation remains under `infrastructure/charity_status/`
