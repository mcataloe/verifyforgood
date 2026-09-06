<!--
LEAP_DOC_METADATA:
  audience: user, maintainer, agent, contributor
  doc_type: documentation-map
  authority: canonical
  applies_to: verifyforgood
END_LEAP_DOC_METADATA
-->

# VerifyForGood Project Documentation

Status: Active canonical entry point  
Owner / approver: Project owner  
Last reconciled: 2026-07-28  
Canonical owner of: Project documentation navigation  
Related Initiatives: `INIT-009`

VerifyForGood enables customers to make evidence-based, explainable decisions about U.S. nonprofits. The platform collects and normalizes source records, preserves provenance and uncertainty, produces transparent derived signals, and evaluates customer-selected or customer-defined rules.

**Customers own the determination of whether a nonprofit is verified, eligible, approved, denied, requires manual review, or has insufficient data for the customer's workflow.** VerifyForGood provides evidence, signals, and deterministic policy execution; it does not make a universal legal, tax, sanctions, compliance, fraud, grant, procurement, or donation-suitability determination.

## Documentation Status

The Brownfield documentation baseline is being established under `INIT-009`. The customer decision-authority principle is approved. Unless a document says otherwise, newly generated Charter, Strategic Outcome, Initiative, Roadmap, Domain, Delivery Unit, and Build Unit content remains **Draft until ratified**.

Merged code, tests, schemas, and contracts remain authoritative for implemented behavior. Planning documents must not claim that proposed behavior is already implemented. Product/package plan intent is now documented in the proposed product catalog source and must still be reconciled with runtime code until a separate implementation Build Unit makes runtime loading or generation catalog-backed.

## Canonical Reading Order

1. [Project Charter](charter/project-charter.md) — Mission, boundaries, governing principles, and non-goals.
2. [Decision Authority](charter/decision-authority.md) — separation of source facts, platform signals, policy results, and customer determinations.
3. [Source of Truth](charter/source-of-truth.md) — document ownership, precedence, lifecycle, and conflict rules.
4. [Strategic Outcomes](strategy/strategic-outcomes.md) — desired observable changes.
5. [Initiative Registry](strategy/initiative-registry.md) — temporary coordinated work advancing outcomes.
6. [Roadmap](strategy/roadmap.md) — timing and priority view.
7. [Domain Map](domains/domain-map.md) — persistent responsibility boundaries.
8. [Architecture Index](architecture/README.md) — technical structure and decisions.
9. [Product Plan Catalog](product/plan-catalog.md) — package meaning, structured plan values, and plan-catalog governance.
10. [Delivery Units](delivery/README.md) — releasable, adoptable, or demonstrable increments.
11. [Build Units](build-units/README.md) — bounded implementation responsibilities.
12. [Governance Records](governance/documentation-inventory.md) — inventory, gaps, migration, drift, and stale sources.

## Project Documentation Areas

| Area | Purpose | Authority |
|---|---|---|
| `docs/charter/` | Mission, boundaries, decision authority, source-truth rules | Canonical or approved principle where stated; otherwise Draft |
| `docs/strategy/` | Outcomes, Initiatives, Roadmap | Draft until ratified |
| `docs/domains/` | Persistent responsibility boundaries | Draft/supporting until ratified |
| `docs/architecture/` | Technical structure and ADRs | Supporting or provisional unless ratified |
| `docs/product/` | Product/package source truth, product-catalog values, and package governance | Proposed canonical where stated; ratify before treating as final product authority |
| `docs/delivery/` | Delivery Unit records | Active planning/source-truth records |
| `docs/build-units/` | Build Unit records | Active planning/source-truth records |
| `docs/deployment/` | Operational deployment runbooks and environment procedures | Supporting; verify against current merged infrastructure before execution |
| `docs/governance/` | Inventory, gaps, drift, migration, stale sources | Supporting governance evidence |
| `docs/implementation/` | Evolving plans and status snapshots | Supporting; inspect lifecycle before use |
| Root `README.md` | Repository overview and compatibility entry point | Supporting, not the owner of all project truth |
| `frontend/docs/` | Customer/developer documentation application | Product runtime, not repository governance documentation |

## Operational Deployment

- [AWS Dev Deployment Runbook](deployment/aws-dev-deployment-runbook.md) — step-by-step Dev deployment procedure, current blockers, verification, and rollback guidance. Treat target-state or `BLOCKED` sections as non-executable until the corresponding infrastructure work is merged and reconciled.

## Current Implementation Authority

For questions about what the software does today, inspect current merged code, tests, schemas, routes, infrastructure configuration, and contracts. Documentation may describe an intended state, but it must identify that state as Draft, Proposed, Transitional, or Historical.

For package/plan questions, start with [Product Plan Catalog](product/plan-catalog.md). Until runtime catalog loading or generation is approved and implemented, also inspect the backend billing code and plan-catalog tests to verify current behavior.

## Stale and Historical Sources

- [Stale / Do-Not-Use Register](governance/stale-document-register.md)
- [Documentation Inventory](governance/documentation-inventory.md)
- [Migration Map](governance/migration-map.md)
- [Drift Ledger](governance/drift-ledger.md)
- [Gap Register](governance/gap-register.md)

Historical Phase identifiers are preserved for traceability. They are classified semantically rather than mechanically renamed.

## Agent Rule

Do not infer customer verification, eligibility, approval, or denial semantics from a field name alone. Start with the [Decision Authority](charter/decision-authority.md), then inspect the implemented contract and the applicable customer policy context.
