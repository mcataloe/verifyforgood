# Frontend Workspace

This directory is the dedicated frontend workspace for future VerifyForGood UI work.

It lives under the repository root so marketing, portal, shared UI foundations, and future frontend docs can evolve together without pushing Node tooling into the Python/Terraform root.

## Package Manager

The frontend workspace is pnpm-first.

- use `pnpm` for install, workspace scripts, dependency updates, and lockfile changes
- `frontend/pnpm-workspace.yaml` is the canonical workspace definition
- `frontend/pnpm-lock.yaml` is the canonical frontend lockfile
- backend Python and Terraform tooling at the repository root stays unchanged

## Naming Baseline

Frontend-facing naming should prefer VerifyForGood and purpose-based terminology.

- use VerifyForGood branding in workspace metadata, docs, UI copy, and new frontend-local identifiers when a product name is needed
- avoid introducing new `charity-status` or `CharityStatusAPI` identifiers in frontend-only code unless they are required for compatibility with existing repo/package boundaries
- the current `@charity-status/*` package scope is intentionally retained for compatibility and staged migration safety
- backend package names, repository paths, and shared package scopes should only be renamed in a dedicated follow-up phase, not opportunistically

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

Public versus protected surfaces:

- `marketing/` and `docs/` are public-facing runtime surfaces
- `portal/` is the protected application surface
- the portal now keeps a small public sign-in boundary inside the app, but authenticated routes stay isolated behind that gate

Current workspace packages:

- `@charity-status/marketing`
- `@charity-status/docs`
- `@charity-status/portal`
- `@charity-status/shared-api`
- `@charity-status/shared-config`
- `@charity-status/shared-ui`
- `@charity-status/shared-types`
- `@charity-status/shared-utils`

These package scopes are internal workspace identifiers, not the preferred public product brand.

## App-Specific vs Shared

App-specific code belongs in `marketing/` or `portal/` when it is tied to that surface's routes, copy, feature wiring, or future product behavior.

Reusable code belongs in `shared/` only when both apps can consume the same implementation without app-specific conditionals.

Current shared UI direction:

- `@charity-status/shared-ui` owns design tokens, Mantine theme mapping, dark mode behavior, and reusable layout/component primitives
- portal and marketing should align to the same typography, spacing, and semantic color system
- reuse shared table, onboarding, entity-detail, and feedback patterns before introducing app-local variants
- accessibility improvements that generalize across apps should land in shared-ui first

All backend HTTP interaction should flow through `@charity-status/shared-api` so request handling, error normalization, route building, and future auth-header injection stay centralized.

Pricing-plan display follows the same rule:

- backend billing entitlements shape the public `GET /v1/plans` catalog
- `@charity-status/shared-types` holds the shared plan metadata contract
- `@charity-status/shared-api` loads the catalog
- `@charity-status/shared-ui` renders plan cards and grids
- marketing and portal keep only surface-specific loading and state composition

Billing interactions follow the same boundary discipline inside the portal:

- frontend billing UI should call abstraction-layer actions such as `createSubscription`, `updatePlan`, and `cancelSubscription`
- those actions must talk to backend billing endpoints, not to Stripe SDK helpers in the browser
- vendor-specific details such as checkout session creation or billing-portal redirects stay behind backend-owned endpoints and feature-local adapters

See `shared/README.md` for the package boundaries inside `frontend/shared/`.

## Commands

Run these from this directory:

```bash
pnpm install
pnpm run format
pnpm run format:check
pnpm run lint
pnpm run test
pnpm run typecheck
pnpm run build
pnpm run dev:docs
pnpm run dev:marketing
pnpm run dev:portal
```

Per-package scripts mirror the same baseline where runtime behavior exists:

- apps (`marketing`, `portal`, `docs`) expose `dev`, `build`, `lint`, `test`, and `typecheck`
- shared runtime/helper packages expose `lint` and `typecheck`, plus `test` where they currently own behavior
- `shared/types` stays type-only for now, so it does not force a placeholder runtime test surface

## Tooling Baseline

- ESLint is centralized in `eslint.config.js`
- Prettier is centralized in `.prettierrc.json` and `.prettierignore`
- Vitest is centralized in `vitest.config.ts` and `vitest.setup.ts`
- package and app TypeScript configs extend `tsconfig.base.json`
- frontend tooling config files are typechecked through `tsconfig.tooling.json`

This keeps the frontend workspace internally consistent without introducing repo-root Node tooling into the Python/Terraform root.

## UX Baseline

The current frontend foundation assumes:

- light and dark themes remain first-class and token-driven
- marketing may be slightly more expressive, but should still inherit the shared visual language
- portal layouts should prioritize calm, data-heavy workflows with reusable entity and table patterns
- loading, empty, and error states should reuse shared feedback primitives where possible

## Adding Apps And Packages

When adding a new frontend app or shared package:

- add it to `pnpm-workspace.yaml` if it is a new top-level workspace root
- extend `tsconfig.base.json` from the package-local `tsconfig.json`
- reuse the centralized ESLint, Prettier, and Vitest configs instead of copying config files into the package
- add package scripts that match the current baseline:
  - apps should expose `dev`, `build`, `lint`, `test`, and `typecheck`
  - shared packages should expose `lint` and `typecheck`, plus `test` once they own real runtime behavior
- keep tests close to the code they exercise under `src/**/*.test.ts` or `src/**/*.test.tsx`
- update this README and any app/package README when the workspace shape changes
