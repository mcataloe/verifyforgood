# Private-Platform Service Areas

This document describes the internal service-area boundaries now defined under:

- `private-platform/src/charity_status_platform/`

These are compatibility-first boundaries. The live implementation still runs from the current `infrastructure/charity_status/` modules, but new private logic should land in these areas rather than extending ad hoc private code paths.

## Identity Access

Package:

- `charity_status_platform.identity_access`

Owns:

- API key auth
- admin key auth
- OAuth client credentials
- auth context providers
- access-policy orchestration

## Customer Accounts

Package:

- `charity_status_platform.customer_accounts`

Owns:

- tenant/customer/account lifecycle
- organization provisioning
- managed credentials
- account-level settings
- control-plane services and stores

## Billing Usage

Package:

- `charity_status_platform.billing_usage`

Owns:

- subscription lifecycle
- Stripe integration
- usage metering and quota enforcement
- hard-stop budget control behavior
- billing/trial/portal workflows

## Admin Operations

Package:

- `charity_status_platform.admin_operations`

Owns:

- internal ops run tracking
- admin workflow helpers
- future operator-facing workflow services

## Runtime

Package:

- `charity_status_platform.runtime`

Owns:

- runtime configuration
- adapter assembly
- handler composition support
- future private entrypoint orchestration

## Notifications

Package:

- `charity_status_platform.notifications`

Reserved for:

- internal notifications
- support workflows
- eventing coordination tied to private platform behavior

## Boundary Rule

These service areas may depend on `charity_status` from `public-core`, but `public-core` must not depend on any `charity_status_platform` package.
