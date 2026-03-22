# Portal App Shell

This package is the starting point for the authenticated customer portal.

## Current structure

- `src/app/`
  - application composition, route definitions, session model, and backend-aligned endpoint hints
- `src/auth/`
  - replaceable auth client abstraction and portal auth state hook
- `src/organization/`
  - active organization/workspace model, loading logic, and portal-wide scope provider
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

- nonprofit verification lookup and search
- organization settings
- billing subscription visibility
- backend-managed checkout, plan change, and billing portal session creation
- OAuth token exchange
- admin-managed API key lifecycle, with a portal-local mock standing in until customer self-serve endpoints exist

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
- roles now use the canonical frontend vocabulary shared across the workspace:
  - `developer`
  - `portal_admin`
  - `customer_admin`
  - `customer_user`
- this phase formalizes typing and helper checks only; it does not introduce route gating or backend authorization policy
- portal UI auth is intentionally not modeled as raw API-key entry in the browser

Current backend integration anchors:

- the backend already normalizes API key and OAuth client-credentials into a shared `AuthContext`
- `POST /v1/oauth/token` exists today and remains an auth integration touchpoint
- future production portal auth can exchange browser identity into backend account/workspace context without changing the portal route-protection boundary

## Organization scope

The portal now treats organization context as the primary scope for user actions.

- the active organization model lives under `src/organization/`
- the provider starts from the authenticated session's `workspace_id`, `account_id`, and `organization_name`
- when a non-mock portal session is available, the provider can hydrate organization settings from `GET /v1/organization/settings`
- future portal features should read organization state and the scoped API client from the provider rather than rebuilding workspace/account context inside each page

The current scoped API client adds portal-local workspace/account headers as placeholder scope hints for future backend integration. This does not replace the backend auth context; it gives the frontend a single place to keep organization scope attached to requests until real browser session integration is wired in.

## Shared foundations used here

- `@charity-status/shared-ui`
  - design tokens, Mantine provider, app shell, navigation schema/filtering, entity detail, onboarding, data table, and feedback primitives
- `@charity-status/shared-config`
  - runtime environment normalization
- `@charity-status/shared-api`
  - backend route/version helpers
- `@charity-status/shared-types`
  - app metadata and organization-context types

## API key management

The portal API access area now includes a minimal API-key management UI.

- customers can list keys, create keys, and revoke keys inside the portal
- plaintext secrets are shown once at creation time and are not persisted in portal storage
- the current implementation is a local mock service scoped to the active organization
- this is intentional because the backend currently exposes API-key lifecycle only through admin control-plane routes:
  - `POST /v1/admin/accounts/{accountId}/api-keys`
  - `GET /v1/admin/accounts/{accountId}/api-keys`
  - `DELETE /v1/admin/accounts/{accountId}/api-keys/{keyId}`

When customer-facing API credential endpoints are added, the portal API-key service should swap from the mock implementation to the shared API client without changing the page-level UI contract.

## Nonprofit search

The dashboard now includes the first core product interaction for portal users:

- exact EIN lookup through `GET /v1/nonprofit/{ein}`
- name-based listing through `GET /v1/nonprofits/search`
- filing enrichment display through `GET /v1/nonprofit/{ein}/filings`

The current implementation is intentionally data-focused:

- exact EIN searches load a detailed verification result
- name searches return summary results and let the user expand a selected nonprofit into the detailed view
- loading, empty, and error states are handled in the dashboard UI

This keeps the initial portal search surface close to the existing backend contract without introducing a heavier search state framework.

The current detail experience also establishes the reusable entity-review layout pattern:

- shared `EntityDetailLayout` for status, EIN, summary fields, actions, and tabs
- shared `StatusBadge`, `PageHeader`, and feedback primitives for consistent review flows
- shared `DataTable` and `FilterBar` for search, filtering, sorting, pagination, loading, and empty states

## Usage and billing visibility

The usage and billing area now uses a small feature-local billing slice under `src/billing/`.

- `GET /v1/organization/billing/subscription` is the source of truth for current plan, effective access, billing status, renewal timing, pending downgrades, and trial state
- `GET /v1/plans` is the source of truth for plan display metadata such as included usage, overage pricing, and feature availability
- `billing.allowOverage` comes from organization settings when available and otherwise follows the documented backend default behavior
- billing actions are abstracted behind a frontend adapter instead of being modeled as Stripe UI flows:
  - `createSubscription(...)` calls `POST /v1/organization/billing/checkout-session`
  - `updatePlan(...)` calls `POST /v1/organization/billing/plan-change`
  - `cancelSubscription(...)` stays vendor-agnostic in the UI and can resolve through `POST /v1/organization/billing/plan-change` or `POST /v1/organization/billing/portal-session`
- request usage is still a portal-local baseline because the backend does not yet expose a customer-facing usage visibility endpoint

This keeps the page useful now without moving billing rules into the frontend. When a real usage endpoint exists, the billing slice should swap its usage source without changing the page-level UI contract.

## Feedback patterns

Portal features now share a small feedback layer for loading, error, empty, and warning states.

- reusable feedback components live under `src/components/feedback/`
- portal hooks normalize shared API client failures through `src/lib/portalError.ts`
- feature slices should use these shared portal patterns before introducing new local loading or error treatments

This keeps nonprofit search, API access, billing visibility, and the auth shell aligned without promoting portal-specific UI concerns into `frontend/shared`.

## Accessibility and theme expectations

- portal routes should keep keyboard navigation and visible focus states intact
- status, alerts, and badges should not rely on color alone
- new screens should reuse shared dark-mode-aware surfaces before adding local color values
- onboarding and dense data views should prefer the shared layouts and table patterns over one-off page composition

## Running the portal

From the workspace root:

```bash
pnpm run dev:portal
```

From this package directly:

```bash
pnpm run dev
pnpm run lint
pnpm run test
pnpm run typecheck
pnpm run build
```

## Extending the portal

- keep app-wide navigation, session composition, and route registration under `src/app/`
- keep portal navigation config in `src/app/portalNavigation.ts` and treat route hashes as the source of navigable destinations
- keep visible nav labels short and scannable; move longer explanatory copy into `helpText` so the shared shell can render it as tooltip metadata
- derive sidebar/navigation rendering from the schema config and centralized filtering helpers instead of embedding role checks in `PortalLayout`
- keep auth concerns isolated under `src/auth/` and UI gating/layout under `src/components/`
- keep API key logic isolated under `src/api-access/` until there is real reuse pressure
- keep usage and billing logic isolated under `src/billing/` until broader frontend reuse is justified
- keep nonprofit lookup/search logic isolated under `src/nonprofits/` until broader cross-app reuse is justified
- add new vertical slices as page-local or feature-local modules before promoting anything to `frontend/shared`
- keep auth wiring abstracted until the real provider and session model are chosen
- align new data access with the existing shared API/config packages and the documented backend contracts

## Intentionally deferred

- production auth integration
- browser-to-backend token exchange or session refresh flow
- full data fetching and mutation workflows
- role/permission matrix
- rich billing or credential management UX
- customer-facing backend API-key endpoints
