<!--
LEAP_DOC_METADATA:
  audience: user, maintainer, agent, contributor
  doc_type: reference
  authority: supporting
  applies_to: verifyforgood
END_LEAP_DOC_METADATA
-->

# Plan Catalog Reference

Status: Active supporting reference; snapshot of implemented plan catalog values
Owner / approver: Billing and Usage domain owner
Last reconciled: 2026-07-03
Canonical owner of: Human-readable summary of the current plan catalog
Related Initiatives: `INIT-006`

## Current Implementation Authority

This table is a convenience snapshot for humans reading plan tiers, limits, and feature availability. It is **not** the source of truth. The implemented plan catalog is defined in code and served at runtime through the public `GET /v1/plans` contract:

- Plan tiers, request/batch limits, rate limits, and overage pricing: `backend/shared/src/verification/backend/shared/billing/service.py` (`DEFAULT_ENTITLEMENTS`)
- Feature-availability mapping and the public catalog payload shape: `backend/shared/src/verification/backend/shared/billing/catalog.py`

If this table and the code disagree, the code and the `/v1/plans` response are authoritative. Update this table when the catalog changes; do not treat it as a spec to implement against.

Monthly subscription price (the recurring seat/plan charge) is managed through Stripe-hosted checkout rather than the `/v1/plans` contract — see [`../implementation/billing-subscription-plan.md`](../implementation/billing-subscription-plan.md) and [`ADR-billing-provider.md`](ADR-billing-provider.md). This table only covers included usage, overage pricing, and feature availability.

## Compare Plans

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

The portal renders this same data as a friendly comparison table on the Compare Plans screen (`frontend/portal/src/pages/ComparePlansPage.tsx`, using `PricingPlanTable` from `frontend/shared/ui/src/components/PricingPlanTable.tsx`), sourced live from `/v1/plans` rather than a hardcoded copy.

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
