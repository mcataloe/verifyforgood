# Private Platform (Scaffold)

This directory marks the future destination for proprietary platform integrations.

Current platform/runtime code still exists in this monorepo:

- `backend/api/`
- `backend/ingest-task/`
- `backend/worker/`
- `infrastructure/verification/platform/`

Target package root after extraction:

- `private-platform/src/verification_platform/`

Scaffolding added in this repo phase:

- `private-platform/src/verification_platform/__init__.py`
- `private-platform/src/verification_platform/README.md`
- `private-platform/src/verification_platform/identity_access/`
- `private-platform/src/verification_platform/customer_accounts/`
- `private-platform/src/verification_platform/billing_usage/`
- `private-platform/src/verification_platform/admin_operations/`
- `private-platform/src/verification_platform/runtime/`
- `private-platform/src/verification_platform/notifications/`

Future private repo responsibilities:

- runtime auth integration
- quota/metering implementation
- proprietary adapters and platform orchestration
- customer/account-specific deployment logic
- all billing and subscription workflow logic
- control-plane and operator workflow orchestration
- backend-owned runtime adapters and transport response shaping
- canonical private backend entrypoint mapping and shared runtime contract exports

Internal service areas now defined:

- `identity_access`
  - API key auth, admin auth, OAuth client credentials, auth context providers
- `customer_accounts`
  - account provisioning, credential management, organization-level settings
- `billing_usage`
  - subscription lifecycle, Stripe flows, usage metering, quota enforcement, budget controls
- `admin_operations`
  - internal ops visibility and admin workflow support
- `runtime`
  - runtime builders, adapter assembly, and handler-side composition support
- `notifications`
  - reserved home for future internal notifications, support, and eventing work

Boundary rule:

- private-platform may depend on public-core
- public-core must not depend on private-platform

Transition helpers now present:

- `verification_platform.runtime.entrypoints`
  - canonical internal map of the live `infrastructure/lambda_*.py` handlers
- `verification_platform.runtime.backend_contracts`
  - compatibility root for API response-envelope and route-version helpers while the live implementation still lives under `verification.api`

