# Billing Subscription Integration Plan

## Summary

This plan defines the documentation-first guardrails for Stripe-backed subscription billing before runtime billing changes begin. The repo already contains billing scaffolding in `infrastructure/charity_status/billing/` and portal billing UI surfaces, so the implementation should extend those seams rather than create a parallel billing model.

The core planning default is:

- `organization_id` is the canonical billing scope.
- Any current `account_id`-based billing persistence is a compatibility bridge until organization-to-control-plane linkage is fully reconciled.

Phase 21D implementation decision:

- Use Stripe Checkout Sessions as the paid subscription initiation flow.
- Keep subscription confirmation webhook-driven rather than treating checkout redirect success as authoritative.

## Implementation Scope

### Organization Billing Identity

- Establish a Stripe customer per organization for paid billing flows.
- Keep portal organization and customer-account services as the source of billing scope.
- Preserve compatibility with current control-plane billing storage while documenting `account_id` as an internal bridge.

### Plan Mapping

- Map Stripe products and prices to the internal plan catalog:
  - `free`
  - `starter`
  - `growth`
  - `pro`
  - `enterprise`
- Preserve existing plan alias handling so external billing requests normalize into the internal plan model.
- Keep plan-to-entitlement resolution backend-owned.

### Checkout and Subscription Creation

- Use backend-created checkout or subscription enrollment flows for paid-plan upgrades.
- Keep frontend billing pages limited to invoking backend-created checkout sessions.
- Do not rely on frontend redirect success as authoritative subscription confirmation.

### Billing Portal and Invoice Visibility

- Use backend-created billing portal sessions for customer self-service.
- Expose invoice and subscription visibility through backend billing endpoints rather than direct frontend Stripe integration.
- Keep customer self-service scoped to the authenticated organization context.

### Webhook Processing and Reconciliation

- Treat Stripe webhooks as the authoritative source for final subscription state transitions.
- Use webhook processing to reconcile checkout completion, subscription lifecycle changes, invoice payments, and payment failures.
- Keep reconciliation idempotent and backend-owned.

### Subscription Lifecycle Synchronization

- Continue persisting local subscription records for entitlement resolution, authorization, and operational visibility.
- Synchronize Stripe-backed lifecycle state into internal subscription records rather than reading Stripe directly at request time.
- Preserve support for pending plan changes and local lifecycle status fields during reconciliation.

### Upgrade and Downgrade Handling

- Support explicit upgrade and downgrade flows through backend billing services.
- Upgrades take effect immediately.
- Downgrades to lower paid plans take effect at the next billing cycle.
- `plan_code=free` is the cancellation request and uses `cancel_at_period_end=true`.
- Resume and uncancel remain implicit through the existing `POST /v1/organization/billing/plan-change` endpoint: a later paid-plan request clears a pending cancellation or replaces it with a scheduled downgrade.
- Preserve backend control over when entitlements and feature access change.

### Graceful Failure and Reconciliation Strategy

- Keep checkout, portal, and webhook processing behind service abstractions that isolate Stripe-specific behavior.
- Preserve local subscription integrity when Stripe interactions fail or webhook delivery is delayed.
- Favor reconciliation and retry-safe backend workflows over frontend-owned assumptions.

## Implementation Constraints

- Organization scope is canonical even if current control-plane services still speak `account_id`.
- Internal subscription records remain required for entitlement resolution and API authorization.
- Frontend billing pages consume backend-created checkout and portal sessions only; billing state is not frontend-owned.
- Free-tier billing behavior remains an explicit policy decision and is not resolved in this phase.
- Stripe webhook events, not checkout success redirects, are the source of truth for final subscription state transitions.
- Phase 21A does not introduce billing code changes, schema migrations, endpoint additions, or Terraform updates.
