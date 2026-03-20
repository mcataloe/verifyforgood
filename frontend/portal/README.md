# Portal App Shell

This package is the starting point for the authenticated customer portal.

## Current structure

- `src/app/`
  - application composition, route definitions, session model, and backend-aligned endpoint hints
- `src/auth/`
  - replaceable auth client abstraction and portal auth state hook
- `src/components/`
  - protected-shell and auth-boundary layout composition
- `src/pages/`
  - top-level placeholder pages for early portal areas plus the public sign-in boundary

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

## Auth boundary

The portal now has one public route inside the app shell:

- `#/sign-in`

Protected routes remain:

- `#/dashboard`
- `#/workspace`
- `#/api-access`
- `#/usage-billing`
- `#/settings`

Route protection is enforced before protected content renders. An unauthenticated user hitting a protected hash is redirected to the sign-in boundary and the requested route is remembered until sign-in succeeds.

## Current auth model

- auth state is portal-local and replaceable through `src/auth/portalAuthClient.ts`
- the current implementation is a mock browser session stored in local storage for local development only
- session state already carries `account_id`, `workspace_id`, `roles`, and `scopes` so the shell does not block future tenant or RBAC work
- portal UI auth is intentionally not modeled as raw API-key entry in the browser

Current backend integration anchors:

- the backend already normalizes API key and OAuth client-credentials into a shared `AuthContext`
- `POST /v1/oauth/token` exists today and remains an auth integration touchpoint
- future production portal auth can exchange browser identity into backend account/workspace context without changing the portal route-protection boundary

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
- keep auth concerns isolated under `src/auth/` and UI gating/layout under `src/components/`
- add new vertical slices as page-local or feature-local modules before promoting anything to `frontend/shared`
- keep auth wiring abstracted until the real provider and session model are chosen
- align new data access with the existing shared API/config packages and the documented backend contracts

## Intentionally deferred

- production auth integration
- browser-to-backend token exchange or session refresh flow
- full data fetching and mutation workflows
- role/permission matrix
- rich billing, usage, or credential management UX
