# Frontend Docs App

This package is the dedicated documentation surface for customers, developers, and internal reference.

## Current structure

- `src/app/`
  - docs composition, lightweight route definitions, and backend-aligned endpoint hints
- `src/components/`
  - docs layout composition
- `src/pages/`
  - content-first placeholder pages for the initial documentation IA

## Initial documentation sections

- getting started
- product overview
- API usage
- integrations
- FAQ

## Shared foundations used here

- `@charity-status/shared-ui`
  - neutral panel primitive and shared base styles
- `@charity-status/shared-config`
  - runtime environment normalization
- `@charity-status/shared-api`
  - route/version helpers for backend-aligned docs references
- `@charity-status/shared-types`
  - app metadata and runtime config typing

## Running the docs app

From the workspace root:

```bash
pnpm run dev:docs
```

From this package directly:

```bash
pnpm run dev
pnpm run lint
pnpm run test
pnpm run typecheck
pnpm run build
```

## Extending the docs app

- keep navigation and section registration under `src/app/`
- keep page content docs-focused; do not import portal workflows or marketing conversion logic
- add richer examples or guides as normal React page modules until a real content pipeline is justified
- use shared foundations only for neutral primitives and backend-aware helper references

## Intentionally deferred

- markdown or MDX pipeline
- CMS integration
- search indexing
- authenticated/internal-only docs workflows
