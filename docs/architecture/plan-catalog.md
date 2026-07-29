<!--
LEAP_DOC_METADATA:
  audience: user, maintainer, agent, contributor
  doc_type: reference
  authority: supporting
  applies_to: verifyforgood
END_LEAP_DOC_METADATA
-->

# Plan Catalog Architecture Reference

Status: Active supporting architecture/runtime reference; superseded for product/package source truth  
Owner / approver: Billing and Usage domain owner  
Last reconciled: 2026-07-28  
Canonical owner of: Runtime projection notes for the implemented plan catalog  
Related Initiatives: `INIT-006`, `INIT-009`

## Source-Truth Notice

This file is no longer the product/package source of truth.

Use [`../product/plan-catalog.md`](../product/plan-catalog.md) for the human-readable package model and [`../product/plan-catalog.yaml`](../product/plan-catalog.yaml) for the structured catalog values after ratification.

This architecture reference only explains how the current backend runtime projects plan data today.

## Current Implementation Authority

As of this reconciliation, the current runtime still defines the operational plan values in code and serves them through the public `GET /v1/plans` contract:

- Plan tiers, request/batch limits, rate limits, overage pricing, aliases, route capabilities, and entitlement behavior: `backend/shared/src/verification/backend/shared/billing/service.py`
- Feature-availability mapping and the public catalog payload shape: `backend/shared/src/verification/backend/shared/billing/catalog.py`

That code remains authoritative for what the software does today until a separate approved Build Unit changes runtime loading or generation. Current implementation authority does not make code the long-term product-governance owner of package meaning.

Future product/package changes should update the product catalog source first, then update or validate runtime projection code in the same bounded change.

Monthly subscription price (the recurring seat/plan charge) is managed through Stripe-hosted checkout rather than the `/v1/plans` contract — see [`../implementation/billing-subscription-plan.md`](../implementation/billing-subscription-plan.md) and [`ADR-billing-provider.md`](ADR-billing-provider.md). The catalog covers included usage, overage pricing, feature availability, route capability mapping, trial posture, and subscription-resolution posture, not Stripe-hosted monthly recurring prices.

## Current Runtime Comparison Snapshot

| | Free | Starter | Growth | Pro | Enterprise |
|---|---|---|---|---|---|
| Monthly requests | 250 | 1,000 | 10,000 | 100,000 | 1,000,000 |
| Batch items | 0 | 0 | 100 | 1,000 | 5,000 |
| Requests per minute | 10 | 30 | 120 | 600 | 5,000 |
| Overage pricing (per request) | $0.005 | $0.004 | $0.003 | $0.002 | $0.001 |
| Verification | Included | Included | Included | Included | Included |
| Risk flags | Not included | Included | Included | Included | Included |
| Financial trends | Not included | Not included | Included | Included | Included |
| Benchmarking | Not included | Not included | Included | Included | Included |
| State registry | Not included | Not included | Not included | Included | Included |
| Monitoring | Not included | Not included | Not included | Included | Included |
| Batch verification | Not included | Not included | Included | Included | Included |
| Organization settings | Not included | Not included | Not included | Included | Included |

The portal renders plan-comparison data from `/v1/plans` rather than from this Markdown table.

## Feature Key Reference

| Table label | `feature_availability` key |
|---|---|
| Verification | `verification` |
| Risk flags | `risk_flags` |
| Financial trends | `financial_trends` |
| Benchmarking | `benchmarking` |
| State registry | `state_registry` |
| Monitoring | `monitoring` |
| Batch verification | `batch_verification` |
| Organization settings | `organization_settings` |
