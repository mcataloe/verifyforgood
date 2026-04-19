# Billing Usage

Purpose:

- private billing, subscription, metering, and quota boundary
- home for Stripe integration, usage enforcement, hard-stop budget controls, and future customer portal billing workflows

Allowed contents:

- subscription lifecycle and plan change logic
- Stripe checkout, portal, and webhook integration
- quota and usage enforcement
- hard-stop budget control behavior and related account-level settings consumption
- billing response shaping for private platform surfaces

Forbidden contents:

- public-core deterministic evaluation logic
- deployment-only configuration

Dependency direction:

- may depend on `verification`
- may depend on customer account services
- public-core must not depend on this package

