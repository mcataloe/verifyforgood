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
- organization-scoped customer API key lifecycle for create, list, and revoke

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
- the current implementation uses the backend portal auth endpoints for login, registration, and current-user hydration
- the browser persists a bearer token in local storage and restores the active session through `GET /v1/auth/me`
- `GET /v1/auth/me` is now the source of truth for whether the signed-in user already has active organization context; session restore no longer depends on a prior browser-local active-organization record
- the public entry screens live in `src/pages/PortalSignInPage.tsx` and `src/pages/PortalRegisterPage.tsx`
- Google and Microsoft buttons remain visible as disabled placeholders; provider exchange is still deferred
- session state already carries `account_id`, `workspace_id`, `roles`, and `scopes` so the shell does not block future tenant or RBAC work
- roles now use the canonical frontend vocabulary shared across the workspace:
  - `developer`
  - `portal_admin`
  - `customer_admin`
  - `customer_user`
- the auth provider restores protected-route access and keeps network/session exchange inside `src/auth/`
- portal UI auth is intentionally not modeled as raw API-key entry in the browser

Current backend integration anchors:

- the backend already normalizes API key and OAuth client-credentials into a shared `AuthContext`
- `POST /v1/oauth/token` exists today and remains an auth integration touchpoint
- future production portal auth can exchange browser identity into backend account/workspace context without changing the portal route-protection boundary
- future provider-based auth should keep the public auth route surfaces and swap the implementation behind `src/auth/portalAuthClient.ts` / `PortalAuthProvider.tsx`

## Organization scope

The portal now treats organization context as the primary scope for user actions.

- the active organization model lives under `src/organization/`
- the provider starts from the authenticated session's `workspace_id`, `account_id`, and `organization_name`
- portal auth restore can promote an existing backend organization membership into the active session before any onboarding gate runs
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

The portal API access area now uses the organization-scoped backend API-key lifecycle.

- customer admins can list keys, create keys, and revoke keys inside the portal
- plaintext secrets are shown once at creation time and are not persisted in browser storage
- the portal uses the current organization routes:
  - `POST /v1/organizations/current/api-keys`
  - `GET /v1/organizations/current/api-keys`
  - `DELETE /v1/organizations/current/api-keys/{keyId}`
- organization-managed API keys themselves cannot access these management routes; portal session auth remains required

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
- `GET /v1/organization/usage` provides the current organization-scoped tracking period, current-period usage totals, and plan-limit context for customer-admin usage visibility
- `GET /v1/plans` is the source of truth for plan display metadata such as included usage, overage pricing, and feature availability
- `billing.allowOverage` comes from organization settings when available and otherwise follows the documented backend default behavior
- backend billing actions remain abstracted behind a frontend adapter instead of being modeled as Stripe UI flows:
  - `createSubscription(...)` calls `POST /v1/organization/billing/checkout-session`
  - `updatePlan(...)` calls `POST /v1/organization/billing/plan-change`
  - `cancelSubscription(...)` stays vendor-agnostic in the UI and can resolve through `POST /v1/organization/billing/plan-change` or `POST /v1/organization/billing/portal-session`
- the customer-admin `Billing` alias is currently read-only and focused on subscription visibility:
  - current plan
  - subscription and billing status
  - billing-cycle timing
  - included limits
  - enabled premium capabilities and feature visibility
- customer-admin payment-management controls are intentionally hidden from this alias in the current phase so the page language stays accurate to the implemented feature set
- request usage now comes from backend org-scoped metering when available, with a plan-based fallback reserved for local demo sessions or backend outages

This keeps the page useful without moving billing rules into the frontend. Future historical usage charts can extend the same billing slice without changing the page-level UI contract.

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

Before running the portal locally, copy `.env.example` to `.env.local` or
`.env.development.local` in this package and point `VITE_API_BASE_URL` at the
AWS dev API Gateway host.

With the current Terraform defaults and custom domain enabled, the dev API host
is expected to be:

```bash
https://dev.charitystatusapi.com
```

For local browser development, the AWS dev API must also allowlist your frontend
origin through the Terraform `cors_allowed_origins` setting. The current dev
defaults include `http://localhost:5173`, `http://127.0.0.1:5173`,
`http://localhost:5174`, and `http://127.0.0.1:5174`.

The AWS dev API is expected to expose the current portal auth and onboarding
routes, including:

- `POST /v1/auth/register`
- `POST /v1/auth/login`
- `GET /v1/auth/me`
- `POST /v1/organizations`
- `GET /v1/plans`

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
- prefer VerifyForGood or purpose-based naming for new portal-local identifiers and contributor docs; keep the existing `@charity-status/*` package scope only where compatibility already depends on it
- keep portal navigation config in `src/app/portalNavigation.ts` and treat route hashes as the source of navigable destinations
- keep role-family selection centralized in `resolvePortalNavigationAudience(...)` so a session resolves to one sidebar information architecture instead of a merged role union
- keep visible nav labels short and scannable; move longer explanatory copy into `helpText` so the shared shell can render it as tooltip metadata instead of inline descriptions
- keep role restrictions hidden in portal navigation; use locked plan behavior only for intentionally discoverable upgrade surfaces
- let the shared shell own sidebar layout structure: app header, summary block, grouped nav body, and footer/profile region
- keep portal-specific summary metadata in the shell summary slot and user/account context in the footer slot through `SidebarProfileSection`
- derive the footer access badge from `getPortalAccessLabel(...)`, which intentionally maps the resolved audience into user-facing labels such as `Admin`, `User`, `Developer`, or `Platform admin`
- do not keep theme controls in the portal sidebar; footer content should stay focused on user and account context
- let the footer expose only a lightweight profile/settings link when a role has that destination in its filtered navigation; do not turn the footer into a second nav cluster
- keep appearance preferences on the profile/settings route so theme selection sits with user-owned preferences instead of shell composition
- the customer-user profile surface now lives in `src/customer-user/CustomerUserProfilePage.tsx`, where account context and `Auto` / `Light` / `Dark` appearance controls share one surface
- organize portal navigation by user mental model:
  - developers: `Overview`, `Tenants`, `Plans`, `Feature Flags`, `Audit`, and `System`
  - portal admins: `Dashboard`, `Customers`, `Subscriptions`, `Support`, `Reports`, and `Settings`
  - customer admins: `Home`, `Team`, `Billing`, `Usage`, `API`, and `Settings`
  - customer users: `Dashboard`, `Search`, and `Automation` in the sidebar, with profile/preferences opened from the footer profile button
- map expanded IA labels onto the closest implemented route surface first by using hash-query navigation aliases instead of inventing duplicate pages
- the current customer-user aliases are:
  - `#/dashboard?nav=customer-user-dashboard`
  - `#/workspace?nav=customer-user-search-ein`
  - `#/workspace?nav=customer-user-search-address`
  - `#/api-access?nav=customer-user-automation-general`
  - `#/api-access?nav=customer-user-automation-api`
  - `#/api-access?nav=customer-user-automation-oauth`
  - `#/settings?nav=customer-user-profile`
- customer-user search and automation panes are local interactive mocks in this phase:
  - `By EIN` and `By Address` reuse the `workspace` route and provide sortable placeholder organization results
  - `Automation > API Key` and `Automation > OAuth` reuse the `api-access` route and persist masked placeholder credentials in browser-local storage only
- when a session can hold multiple roles, keep the audience-priority order in `resolvePortalNavigationAudience(...)` in sync with product intent so the sidebar stays deterministic
- derive sidebar/navigation rendering from the schema config and centralized filtering helpers instead of embedding role checks in `PortalLayout`
- keep auth concerns isolated under `src/auth/` and UI gating/layout under `src/components/`
- keep the portal entry UX in `src/pages/PortalSignInPage.tsx`; if real provider wiring lands, push network/session exchange into `src/auth/` rather than embedding it in the page
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
