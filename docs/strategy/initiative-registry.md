<!--
LEAP_DOC_METADATA:
  audience: user, maintainer, agent, contributor
  doc_type: initiative-registry
  authority: draft
  applies_to: verifyforgood
END_LEAP_DOC_METADATA
-->

# VerifyForGood Initiative Registry

Status: Draft pending project-owner ratification  
Owner / approver: Project owner  
Last reconciled: 2026-07-02  
Canonical owner of: Temporary coordinated work after ratification

Initiatives are temporary, outcome-oriented bodies of coordinated work. Repository evidence supports the portfolio below, but status remains conservative where completed historical Phases do not prove that the broader Initiative is complete.

## Portfolio Summary

| ID | Initiative | Status | Outcomes | Roadmap placement |
|---|---|---|---|---|
| `INIT-001` | Customer-Owned Verification and Decision Policy | Needs Reconciliation | `SO-002`, `SO-003`, `SO-004`, `SO-005`, `SO-007`, `SO-008` | Next |
| `INIT-002` | Evidence, Provenance, and Uncertainty | Active / Needs Reconciliation | `SO-001`, `SO-003`, `SO-004`, `SO-005`, `SO-006` | Unscheduled |
| `INIT-003` | Regulatory Data Ingestion and Freshness | Active / Needs Reconciliation | `SO-001`, `SO-005`, `SO-006`, `SO-008` | Unscheduled |
| `INIT-004` | Customer Identity, Organizations, and Policy Administration | Active / Needs Reconciliation | `SO-002`, `SO-003`, `SO-007`, `SO-008` | Unscheduled |
| `INIT-005` | Customer API and Portal Experience | Active / Needs Reconciliation | `SO-001`, `SO-002`, `SO-004`, `SO-005`, `SO-007` | Unscheduled |
| `INIT-006` | Billing, Usage, and Subscription Productization | Needs Reconciliation | `SO-007`, `SO-008` | Unscheduled |
| `INIT-007` | Public-Core / Private-Platform / Infrastructure Separation | Active | `SO-008` | Later / active enabling work |
| `INIT-008` | Public Product, Developer, and Documentation Experience | Active / Early | `SO-001`, `SO-004`, `SO-007` | Unscheduled |
| `INIT-009` | LEAP Documentation and Traceability Baseline | Active | `SO-002`, `SO-004`, `SO-007`, `SO-008` | Now |

## INIT-001 — Customer-Owned Verification and Decision Policy

- **Purpose:** Align policy semantics, customer authority, rule configuration, auditability, public terminology, and compatibility behavior.
- **Success criteria:** Approved authority matrix; customer policy scope/precedence/versioning defined; current fields have a compatibility plan; policy results are reproducible; public claims match authority.
- **Non-goals:** Implement semantic or API changes without a separate Recon and approval; provide legal/compliance conclusions.
- **Affected Domains:** Customer Decision Policy, Customer Decision Audit, Scoring and Derived Signals, Evidence and Provenance, Identity and Access, Customer Organizations, API and Developer Platform, Portal Experience, Public Marketing and Documentation.
- **Repositories:** `mcataloe/verifyforgood`; LEAP Framework only as external methodology.
- **Dependencies:** Project Charter, Decision Authority, current policy/decision contracts, authorization model, Architecture boundary decision.
- **Risks:** High user-trust, contract, policy, legal/compliance wording, data history, and authorization risk.
- **Known Delivery Units:** Decision Authority and Semantic Contract; Customer Policy Definition and Versioning; Policy Administration; API Compatibility Transition; Decision Evidence and Audit History.
- **Owner / approver:** Project owner; additional legal/security/Architecture owners as scope requires.
- **Evidence:** Current scoring, decision, policy, settings, verification orchestration, tests, and approved owner clarification.

## INIT-002 — Evidence, Provenance, and Uncertainty

- **Purpose:** Keep source evidence, transformation history, freshness, conflicts, and derived outputs inspectable and honest.
- **Success criteria:** Material signals trace to evidence; uncertainty states remain distinct; evidence contracts are testable.
- **Non-goals:** Declare suitability or customer eligibility from data presence alone.
- **Affected Domains:** Source Acquisition, Organization Verification Evidence, Evidence and Provenance, Scoring and Derived Signals, Customer Decision Audit.
- **Dependencies:** Source adapters, normalization, evidence builder, profile contracts, `INIT-001` semantics.
- **Risks:** Staleness, source conflict, misleading confidence, and incomplete provenance.
- **Known Delivery Units:** Needs reconciliation from existing evidence/scoring Phases.
- **Owner / approver:** Project owner / future Domain owner.
- **Evidence:** Current evidence, source, scoring, materialization, and test modules.

## INIT-003 — Regulatory Data Ingestion and Freshness

- **Purpose:** Acquire, normalize, refresh, and operationally observe regulatory nonprofit and filing data.
- **Success criteria:** Repeatable runs; explicit source/freshness metadata; recoverable errors; current profiles refresh without silent corruption.
- **Non-goals:** Treat source ingestion as an eligibility conclusion.
- **Affected Domains:** Source Acquisition, Regulatory Filing Ingestion, Evidence and Provenance, Administration and Operations, Infrastructure and Deployment.
- **Dependencies:** IRS publication formats, S3/Athena/Glue/DynamoDB, orchestration, runbooks.
- **Risks:** Source changes, partial runs, stale profiles, cost, and operational failure.
- **Known Delivery Units:** Historical Form 990 and monthly-ingest Phases; precise mapping needs reconciliation.
- **Owner / approver:** Project owner / ingestion owner.
- **Evidence:** Form 990 plans, monthly architecture/runbook, ingest code and tests.

## INIT-004 — Customer Identity, Organizations, and Policy Administration

- **Purpose:** Provide organization-scoped identity, membership, settings, authorization, credentials, and future policy administration.
- **Success criteria:** Customer resources are correctly scoped; roles and authorization are explicit; organization settings are auditable; future policy administration has approved controls.
- **Non-goals:** Add policy CRUD or auth changes under `INIT-009`.
- **Affected Domains:** Identity and Access, Customer Organizations, Customer Decision Policy, Customer Decision Audit, Portal Experience, API and Developer Platform.
- **Dependencies:** Identity datastore ADR, auth models, customer account services, `INIT-001` policy contract.
- **Risks:** Identity, authorization, tenant isolation, privacy, and audit risk.
- **Known Delivery Units:** Historical tenant-aware API and customer-administration Phases; needs reconciliation.
- **Owner / approver:** Project owner / security and identity owner.
- **Evidence:** Identity plans/status, portal, auth/control-plane code, tests.

## INIT-005 — Customer API and Portal Experience

- **Purpose:** Deliver stable customer-facing API and portal workflows over shared product contracts.
- **Success criteria:** Customer workflows function end to end; terminology is consistent; unknown/error states are honest; accessibility and contract compatibility are validated.
- **Non-goals:** Invent policy semantics in UI copy or bypass authorization.
- **Affected Domains:** API and Developer Platform, Portal Experience, Organization Verification Evidence, Customer Organizations, Public Marketing and Documentation.
- **Dependencies:** `INIT-001`, `INIT-002`, `INIT-004`, shared types/contracts.
- **Risks:** Contract drift, misleading labels, accessibility regressions, and cross-surface inconsistency.
- **Known Delivery Units:** Historical frontend, tenant-aware API, and customer-administration work.
- **Owner / approver:** Project owner / product and frontend owners.
- **Evidence:** API routes, portal code/tests, frontend READMEs, customer docs.

## INIT-006 — Billing, Usage, and Subscription Productization

- **Purpose:** Provide plan entitlements, usage enforcement, hosted billing workflows, and customer billing visibility.
- **Success criteria:** Billing state and product access are consistent; customer-visible pricing is backend/Stripe-authored; production decisions are documented; failure states preserve customer access rules.
- **Non-goals:** Resolve taxes, refunds, fees, or production readiness without approval.
- **Affected Domains:** Billing and Usage, Customer Organizations, Identity and Access, API and Developer Platform, Portal Experience.
- **Dependencies:** Stripe ADR, plans, entitlements, auth, customer account data, support operations.
- **Risks:** Money movement, pricing truth, taxes, refunds, failed-payment behavior, and user trust.
- **Known Delivery Units:** Historical Phase 12 and Phase 21 billing work; broader Initiative completion needs reconciliation.
- **Owner / approver:** Project owner / billing owner.
- **Evidence:** Billing plan/status, code/tests, customer README, pricing runtime status.

## INIT-007 — Public-Core / Private-Platform / Infrastructure Separation

- **Purpose:** Separate reusable deterministic domain logic, customer-private platform concerns, and deployment assets while preserving compatibility.
- **Success criteria:** Dependency direction is enforced; mixed concerns are reduced; current runtime remains stable; extraction can occur reversibly.
- **Non-goals:** Physically split repositories or move code without staged approval.
- **Affected Domains:** All technical Domains; especially Infrastructure and Deployment, Customer Organizations, Billing and Usage, Customer Decision Policy.
- **Dependencies:** Target architecture, split guide/plan, compatibility tests, current runtime imports.
- **Risks:** Import/contract breakage, misplaced customer policy data, deployed-resource disruption.
- **Known Delivery Units:** Stage-1 readiness, split scaffolding, future seam extraction.
- **Owner / approver:** Project owner / Architecture owner.
- **Evidence:** Target architecture, split plan/guide, scaffolding tests and READMEs.

## INIT-008 — Public Product, Developer, and Documentation Experience

- **Purpose:** Present clear public product messaging, developer guidance, and customer documentation consistent with implemented contracts and authority.
- **Success criteria:** Marketing, docs, and developer surfaces are navigable, accurate, accessible, and aligned with source truth.
- **Non-goals:** Publish unsupported compliance or production-readiness claims.
- **Affected Domains:** Public Marketing and Documentation, API and Developer Platform, Portal Experience.
- **Dependencies:** `INIT-001`, `INIT-005`, brand/configuration, frontend architecture.
- **Risks:** Misleading claims, stale pricing, documentation/runtime drift.
- **Known Delivery Units:** Marketing/docs application shells and historical frontend work.
- **Owner / approver:** Project owner / product documentation owner.
- **Evidence:** Marketing, docs, shared UI, customer README, frontend tests.

## INIT-009 — LEAP Documentation and Traceability Baseline

- **Purpose:** Establish a discoverable, internally consistent Mission-to-Build-Unit documentation baseline and reconcile existing documents without changing runtime behavior.
- **Success criteria:** Entry point, Charter, decision authority, outcomes, Initiative registry, Roadmap, Domain map, Architecture index, Delivery/Build records, governance registers, and validation exist.
- **Non-goals:** Change APIs, runtime policy behavior, schemas, billing, auth, infrastructure, or delete/move existing documents.
- **Affected Domains:** All documentation and Architecture views; no runtime Domain behavior changes.
- **Dependencies:** Approved Recon, current repository evidence, LEAP documentation model.
- **Risks:** Source-truth duplication, path breakage, accidental ratification, trust-language drift.
- **Known Delivery Units:** `DU-GOV-001`, `DU-GOV-002`.
- **Owner / approver:** Project owner.
- **Evidence:** `INIT-009` LHS and governance records.

## Registry Rules

- Status must be supported by evidence.
- Completed historical Phases do not automatically complete a broader Initiative.
- `Needs Reconciliation` is preferred over invented certainty.
- Initiative identity is independent of Roadmap placement.
- Initiative changes require updates to affected Outcome, Domain, Delivery, and drift records.
