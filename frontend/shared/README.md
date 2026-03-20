# Shared Frontend Foundations

This directory contains the intentionally reusable frontend building blocks for both `marketing` and `portal`.

Current package boundaries:

- `ui/`
  - design tokens, theme variables, layout primitives, and minimal shared UI building blocks
- `types/`
  - shared TypeScript contracts for app metadata, runtime config, and backend transport envelopes
- `api/`
  - backend-aligned route helpers and a small envelope-aware JSON request client
- `utils/`
  - tiny pure helpers that are generic enough to stay app-agnostic
- `config/`
  - shared runtime-environment normalization and API config helpers

## Dependency Direction

- `ui` may depend on `types` and `utils`
- `api` may depend on `types` and `config`
- `config` may depend on `types`
- apps may depend on any shared package
- shared packages must not depend on `marketing` or `portal`

## What Belongs In Shared

- backend transport contracts that mirror the standard API envelope
- generic request helpers that work for either app
- small UI primitives with no app-specific state or copy
- runtime config normalization used by both apps
- pure formatting or string helpers

## What Must Stay App-Local

- portal-specific billing, settings, or authenticated workflow state
- marketing-specific messaging, page composition, and campaign presentation
- app-specific route loaders, page data orchestration, and feature flags
- any helper whose name or behavior only makes sense for one app

## Anti-Patterns

- using `shared/` as a junk drawer for unrelated helpers
- moving app code into shared just because it is convenient
- coupling shared packages to private admin-only or portal-only flows before both apps need them
- creating large design-system or API-client abstractions before the duplication actually exists

## Intentionally Deferred

- no shared `assets/` package yet; there is no justified cross-app asset set in this phase
- no full design system, data-cache layer, or endpoint-specific SDK yet
