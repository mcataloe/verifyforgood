# Portal App Shell

This package is the starting point for the authenticated customer portal.

## Current structure

- `src/app/`
  - application composition, route definitions, session stub, and backend-aligned endpoint hints
- `src/components/`
  - portal layout composition
- `src/pages/`
  - top-level placeholder pages for early portal areas

## Top-level portal areas

- dashboard
- workspace
- API access
- usage and billing
- settings

These are intentionally placeholder-first, but they align to the customer-facing backend capabilities that already exist today:

- organization settings
- billing subscription visibility
- Stripe checkout and customer portal session creation
- OAuth token exchange

## Shared foundations used here

- `@charity-status/shared-ui`
  - panel primitive and shared styling
- `@charity-status/shared-config`
  - runtime environment normalization
- `@charity-status/shared-api`
  - backend route/version helpers
- `@charity-status/shared-types`
  - app metadata and organization-context types

## Running the portal

From the workspace root:

```bash
npm run dev:portal
```

From this package directly:

```bash
npm run dev
npm run lint
npm run test
npm run typecheck
npm run build
```

## Extending the portal

- keep app-wide navigation, session composition, and route registration under `src/app/`
- add new vertical slices as page-local or feature-local modules before promoting anything to `frontend/shared`
- keep auth wiring abstracted until the real provider and session model are chosen
- align new data access with the existing shared API/config packages and the documented backend contracts

## Intentionally deferred

- production auth integration
- full data fetching and mutation workflows
- role/permission matrix
- rich billing, usage, or credential management UX
