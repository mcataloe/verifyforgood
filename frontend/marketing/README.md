# Marketing App Shell

This package is the starting point for the public-facing marketing application.

## Current structure

- `src/app/`
  - site composition, lightweight route definitions, and backend-aligned public endpoint hints
- `src/components/`
  - public-site layout composition
- `src/pages/`
  - top-level marketing pages for the early customer journey

## Top-level public pages

- home
- product
- pricing
- security and trust
- developers
- contact and demo
- login entry point

These remain placeholder-first, but the IA is deliberate and keeps public content separate from the authenticated portal shell.

## Shared foundations used here

- `@charity-status/shared-ui`
  - design tokens, Mantine provider, theme toggle, feedback primitives, and marketing section primitives
- `@charity-status/shared-config`
  - runtime environment normalization
- `@charity-status/shared-api`
  - route/version helpers for public API references
- `@charity-status/shared-types`
  - app metadata and runtime config typing

## Running the marketing app

Before running the marketing app locally, copy `.env.example` to `.env.local`
or `.env.development.local` in this package and point:

- `VITE_API_BASE_URL` at the customer API host
- `VITE_PLATFORM_BASE_URL` at the platform app host

With the current Terraform defaults and custom domain enabled, the dev API host
is expected to be:

```bash
https://dev.charitystatusapi.com
```

If the dev custom domain is disabled in AWS, replace this with the API Gateway
invoke URL for the dev stage instead.

For local browser development, the AWS dev API must also allowlist your
frontend origin through the Terraform `cors_allowed_origins` setting. The
current dev defaults include `http://localhost:5174` and
`http://127.0.0.1:5174`.

The public pricing page depends on the backend-authored:

- `GET /v1/plans`
- platform/login handoff now uses `VITE_PLATFORM_BASE_URL` so the public site
  can redirect into the dedicated platform runtime instead of rendering a
  same-app placeholder

Docker container build:

```powershell
docker build -f frontend/marketing/Dockerfile frontend
```

Local compose host:

- `http://localhost:5174`

From the workspace root:

```bash
pnpm run dev:marketing
```

From this package directly:

```bash
pnpm run dev
pnpm run lint
pnpm run test
pnpm run typecheck
pnpm run build
```

## Extending the marketing app

- keep page registration and navigation in `src/app/`
- keep page-specific messaging and content modules app-local unless they become genuinely cross-site
- use shared foundations for neutral primitives, marketing section scaffolds, and API/runtime helpers, not for marketing copy or conversion logic
- the pricing page should consume the backend-authored `GET /v1/plans` catalog through shared types/API helpers rather than hardcoded local plan data
- keep docs, SEO, analytics, and CMS decisions deferred until requirements are concrete

## Theme alignment expectations

- marketing should inherit the same core token system as the portal
- typography, spacing, button, card, and input treatment should stay visually continuous with shared-ui
- marketing can be slightly more expressive through composition and copy, but should not fork the core palette or dark mode behavior

## Intentionally deferred

- CMS or blog infrastructure
- strong SEO metadata infrastructure
- analytics and attribution tooling
- public docs runtime integration
