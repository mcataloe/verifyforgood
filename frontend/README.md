# Frontend Workspace

This directory is the dedicated frontend workspace for future VerifyForGood UI work.

It lives under the repository root so marketing, portal, shared UI foundations, and future frontend docs can evolve together without pushing Node tooling into the Python/Terraform root.

## Directory Purpose

- `marketing/`
  - public-facing marketing site shell
- `portal/`
  - authenticated customer portal shell
- `shared/`
  - reusable frontend code and documented shared boundaries
- `docs/`
  - documentation application shell for customer, developer, and internal reference content

## Dependency Direction

- `marketing` must not depend on `portal`
- `portal` must not depend on `marketing`
- both apps may depend on `shared/*`
- `docs/` remains separate from marketing and portal runtime logic

Current workspace packages:

- `@charity-status/marketing`
- `@charity-status/docs`
- `@charity-status/portal`
- `@charity-status/shared-api`
- `@charity-status/shared-config`
- `@charity-status/shared-ui`
- `@charity-status/shared-types`
- `@charity-status/shared-utils`

## App-Specific vs Shared

App-specific code belongs in `marketing/` or `portal/` when it is tied to that surface's routes, copy, feature wiring, or future product behavior.

Reusable code belongs in `shared/` only when both apps can consume the same implementation without app-specific conditionals.

See `shared/README.md` for the package boundaries inside `frontend/shared/`.

## Commands

Run these from this directory:

```bash
npm install
npm run typecheck
npm run build
npm run dev:docs
npm run dev:marketing
npm run dev:portal
```
