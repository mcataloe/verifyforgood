# Billing Provider Selection

## Status

provisional

## Decision

Use Stripe as the billing provider for customer subscriptions, plan changes, invoice retrieval, and future tax support.

## Context

- The platform needs tenant-aware billing tied to organizations.
- Customer organizations need self-service billing flows for checkout, plan lifecycle changes, and invoice visibility.
- Upgrade and downgrade behavior must be explicit and consistent with organization-scoped entitlements.
- The billing architecture needs a path to Stripe Tax and webhook-driven reconciliation without reworking the core subscription model.

## Consequences

- Billing state must remain organization-scoped, with `organization_id` treated as the canonical billing scope.
- Current `account_id`-based billing/control-plane persistence is a compatibility bridge and should not redefine the billing model.
- Internal subscription state must not depend solely on frontend assumptions or redirect outcomes.
- Webhook reconciliation is required for authoritative synchronization of Stripe state back into local subscription records.
- The existing `BillingCheckoutService`, `BillingPortalService`, and `StripeWebhookService` remain the integration seams for Stripe-backed billing.
- Stripe-specific HTTP and SDK behavior must stay inside billing-provider adapters rather than leaking into handlers, repositories, or frontend contracts.
- Portal identity and customer-account services remain the source of organization scope; Stripe ids are attached billing state, not primary identity.
