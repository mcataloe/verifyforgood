<!--
LEAP_DOC_METADATA:
  audience: user, maintainer, agent, contributor
  doc_type: product-plan-catalog
  authority: canonical-after-ratification
  applies_to: verifyforgood
END_LEAP_DOC_METADATA
-->

# VerifyForGood Plan Catalog

Status: Proposed canonical product/package source — pending project-owner ratification  
Owner / approver: Project owner and Billing and Usage domain owner  
Last reconciled: 2026-07-28  
Canonical owner of: Product/package plan meaning, included usage, feature availability, overage posture, and plan-catalog change process after ratification  
Related Initiatives: `INIT-006`, `INIT-009`

## Purpose

This document is the human-readable source for VerifyForGood package meaning. It explains what each plan is intended to include, what the current runtime implements, and which related behavior is intentionally outside the plan catalog.

The exact machine-readable catalog lives beside this document in [`plan-catalog.yaml`](plan-catalog.yaml). That file is intentionally JSON-compatible YAML so it can be validated with Python standard-library tooling until the project explicitly approves a YAML parser or runtime catalog loader.

## Current Runtime Reality

As of this reconciliation, the current backend runtime still defines plan entitlements in `backend/shared/src/verification/backend/shared/billing/service.py` and builds the public `GET /v1/plans` payload in `backend/shared/src/verification/backend/shared/billing/catalog.py`.

That current code remains the operational authority for what the software does today. This document and `plan-catalog.yaml` define the intended product-governance direction: package meaning should be document-owned, and runtime code should become a projection of the structured catalog or be validated against it.

Do not claim runtime behavior changed because this document exists. Runtime loading or generation from the structured catalog requires a separate approved Build Unit.

## Change Rule

After this source is ratified:

1. Product/package intent changes start in this document.
2. Exact value changes start in `docs/product/plan-catalog.yaml`.
3. Runtime projection code and tests are updated in the same bounded change.
4. `GET /v1/plans` remains a public runtime projection, not an independent product-governance authority.
5. Any change to billing, entitlement enforcement, trial behavior, overage behavior, Stripe behavior, or public response shape must follow the repository stop conditions.

## Stripe Monthly Price Boundary

This catalog covers included usage, rate limits, overage unit pricing, feature availability, route capabilities, plan aliases, trial posture, and subscription-resolution behavior.

It does not define customer-facing monthly subscription prices. Monthly recurring prices are configured through Stripe-hosted Checkout unless the project owner makes a separate decision to move those prices into repository-governed source truth.

## Plan Summary

| Plan | Monthly requests | Batch items | Requests/minute | Overage per request | Included capabilities |
|---|---:|---:|---:|---:|---|
| Free | 250 | 0 | 10 | $0.005 | Verification |
| Starter | 1,000 | 0 | 30 | $0.004 | Verification; risk flags |
| Growth | 10,000 | 100 | 120 | $0.003 | Verification; risk flags; financial trends; benchmarking; batch verification |
| Pro | 100,000 | 1,000 | 600 | $0.002 | Growth capabilities plus state registry, monitoring, organization settings |
| Enterprise | 1,000,000 | 5,000 | 5,000 | $0.001 | Pro capabilities with higher usage and rate limits |

## Plan Codes and Aliases

Canonical plan codes:

- `free`
- `starter`
- `growth`
- `pro`
- `enterprise`

Compatibility aliases:

| Alias | Resolves to |
|---|---|
| `developer` | `free` |
| `team` | `growth` |
| `business` | `pro` |

Preserve aliases unless a separately approved compatibility migration removes them.

## Feature Availability

| Feature | Free | Starter | Growth | Pro | Enterprise |
|---|---|---|---|---|---|
| Verification | Included | Included | Included | Included | Included |
| Risk flags | Not included | Included | Included | Included | Included |
| Financial trends | Not included | Not included | Included | Included | Included |
| Benchmarking | Not included | Not included | Included | Included | Included |
| State registry | Not included | Not included | Not included | Included | Included |
| Monitoring | Not included | Not included | Not included | Included | Included |
| Batch verification | Not included | Not included | Included | Included | Included |
| Organization settings | Not included | Not included | Not included | Included | Included |

## Route Capability Map

| Route | Capability |
|---|---|
| `POST /v1/verify` | `verification` |
| `POST /v1/nonprofits/verify` | `verification` |
| `POST /v1/verify/batch` | `batch_verification` |
| `GET /v1/nonprofit/{ein}` | `verification` |
| `GET /v1/nonprofits/{ein}` | `verification` |
| `GET /v1/nonprofit/{ein}/filings` | `verification` |
| `GET /v1/nonprofits/search` | `verification` |
| `GET /v1/nonprofits/{ein}/sources` | `financial_trends` |
| `GET /v1/nonprofits/{ein}/sources/{source_name}` | `financial_trends` |
| `GET /v1/nonprofits/{ein}/compliance` | `risk_flags` |
| `GET /v1/nonprofits/{ein}/federal-awards` | `risk_flags` |

Feature-restricted routes currently require both the route capability and the matching feature flag where applicable.

## Trial Behavior

Eligible organizations receive a 14-day no-card free trial. Current documented behavior:

- The trial starts on the first authenticated customer product request made with an issued credential.
- The trial grants Growth-tier entitlements while the underlying billing plan remains `free`.
- The trial does not automatically create a paid subscription.
- The trial does not automatically charge the customer when it ends.
- When the trial expires, the organization falls back to Free-tier entitlements unless it has explicitly upgraded.
- Upgrading to a paid plan remains a separate explicit action through Stripe-hosted Checkout.

## Overage Behavior

Current documented behavior:

- Pay-per-request overage is enabled by default for all plans.
- Customers can disable account-wide overage with `billing.allowOverage=false`.
- When overage is disabled, requests that would exceed the included monthly limit return `429`.

## Subscription Resolution Behavior

Current implemented and tested behavior:

- If no subscription is found, the fallback plan is `free` unless a valid fallback plan is provided.
- Inactive subscriptions fall back to `free` entitlements.
- Active subscriptions keep the current plan during pending downgrades or pending cancellation until the pending effective date.
- Active trials on a Free billing plan can temporarily resolve to Growth entitlements.

## Public Plan Catalog Projection

`GET /v1/plans` should expose a public catalog suitable for pricing and plan-comparison UI surfaces. The current payload shape includes:

- `plan_code`
- `display_name`
- `included_usage.monthly_requests`
- `included_usage.batch_items`
- `included_usage.requests_per_minute`
- `per_request_pricing.amount_usd_micros`
- `per_request_pricing.currency_code`
- `per_request_pricing.unit`
- `feature_availability`

This endpoint must not include tenant-specific billing state.

## Validation Expectations

Catalog validation should ensure:

- `plan-catalog.yaml` matches current backend entitlements while runtime remains code-backed.
- `plan-catalog.yaml` matches the public `GET /v1/plans` payload projection.
- plan aliases remain documented and tested.
- route capabilities and feature requirements remain documented and tested.
- trial, overage, and subscription fallback behavior are documented and covered by targeted tests.

## Open Governance Note

This document is approved as the target product-governance direction by the project owner in the conversation that requested this implementation. The repository should still treat this as pending ratification until the commit/PR trail records the decision in the standard project governance process.
