# Private Platform (Scaffold)

This directory marks the future destination for proprietary platform integrations.

Current platform/runtime code still exists in this monorepo:

- `infrastructure/lambda_query.py`
- `infrastructure/lambda_refresh.py`
- `infrastructure/eo_bmf_ingest_worker.py`
- `infrastructure/lambda_form990.py`
- `infrastructure/charity_status/platform/`

Target package root after extraction:

- `private-platform/src/charity_status_platform/`

Scaffolding added in this repo phase:

- `private-platform/src/charity_status_platform/__init__.py`
- `private-platform/src/charity_status_platform/README.md`
- `private-platform/src/charity_status_platform/identity_access/`
- `private-platform/src/charity_status_platform/customer_accounts/`
- `private-platform/src/charity_status_platform/billing_usage/`
- `private-platform/src/charity_status_platform/admin_operations/`
- `private-platform/src/charity_status_platform/runtime/`
- `private-platform/src/charity_status_platform/notifications/`

Future private repo responsibilities:

- runtime auth integration
- quota/metering implementation
- proprietary adapters and platform orchestration
- customer/account-specific deployment logic
- all billing and subscription workflow logic
- control-plane and operator workflow orchestration
- Lambda entrypoints and transport response shaping
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

- `charity_status_platform.runtime.entrypoints`
  - canonical internal map of the live `infrastructure/lambda_*.py` handlers
- `charity_status_platform.runtime.backend_contracts`
  - compatibility root for API response-envelope and route-version helpers while the live implementation still lives under `charity_status.api`
