# Private-Platform Service Areas

This document describes the internal service-area boundaries now defined under:

- `private-platform/src/verification_platform/`

These are compatibility-first boundaries. The live implementation still runs from the current `infrastructure/verification/` modules, but new private logic should land in these areas rather than extending ad hoc private code paths.

## Identity Access

Package:

- `verification_platform.identity_access`

Owns:

- API key auth
- admin key auth
- OAuth client credentials
- auth context providers
- access-policy orchestration

## Customer Accounts

Package:

- `verification_platform.customer_accounts`

Owns:

- tenant/customer/account lifecycle
- organization provisioning
- managed credentials
- account-level settings
- control-plane services and stores

## Billing Usage

Package:

- `verification_platform.billing_usage`

Owns:

- subscription lifecycle
- Stripe integration
- usage metering and quota enforcement
- hard-stop budget control behavior
- billing/trial/portal workflows

## Admin Operations

Package:

- `verification_platform.admin_operations`

Owns:

- internal ops run tracking
- admin workflow helpers
- future operator-facing workflow services

## Runtime

Package:

- `verification_platform.runtime`

Owns:

- runtime configuration
- adapter assembly
- handler composition support
- future private entrypoint orchestration

## Notifications

Package:

- `verification_platform.notifications`

Reserved for:

- internal notifications
- support workflows
- eventing coordination tied to private platform behavior

## Boundary Rule

These service areas may depend on `verification` from `public-core`, but `public-core` must not depend on any `verification_platform` package.

