<!--
LEAP_DOC_METADATA:
  audience: user, maintainer, agent, contributor
  doc_type: project-charter
  authority: draft
  applies_to: verifyforgood
END_LEAP_DOC_METADATA
-->

# VerifyForGood Project Charter

Status: Draft — customer decision-authority principle approved  
Owner / approver: Project owner  
Last reconciled: 2026-07-02  
Canonical owner of: Mission, boundaries, governing intent, and non-goals after ratification  
Related Strategic Outcomes: `SO-001` through `SO-008`  
Related Initiatives: All; especially `INIT-001` and `INIT-009`

## 1. Mission

VerifyForGood enables customers to make their own evidence-based, explainable decisions about U.S. nonprofits. It collects and normalizes source records, preserves provenance and uncertainty, produces transparent derived signals, and evaluates customer-selected or customer-defined rules.

Customers—not VerifyForGood—determine whether a nonprofit is verified, eligible, approved, denied, requires manual review, or has insufficient data for their particular workflow.

## 2. Who the Platform Serves

VerifyForGood is intended to support organizations and teams that need repeatable, explainable review of U.S. nonprofits, including customer operations, grantmaking, corporate social responsibility, procurement, finance, compliance-support, developer, and integration workflows.

This list describes potential and current users; it does not establish that every workflow is production-ready or legally authoritative.

## 3. Problem Statement

Relevant nonprofit information is distributed across source systems, filing periods, formats, and jurisdictions. Customers must often reconcile source identity, freshness, missing evidence, conflicting records, derived risk signals, and their own internal decision rules.

Without explicit separation between evidence and decisions, a platform-generated score or status can be mistaken for a universal conclusion. VerifyForGood exists to make the evidence and transformation path inspectable while allowing each customer to govern its own operational outcome.

## 4. Governing Intent

VerifyForGood should:

- preserve source identity, source IDs, retrieval time, reporting period, and transformation history
- keep raw evidence separable from normalized data and derived interpretation when practical
- distinguish source facts, normalized facts, derived signals, baseline evaluations, policy results, and customer determinations
- represent uncertainty and source conflicts honestly
- execute deterministic and explainable rules
- preserve stable API and product contracts unless a separately approved transition changes them
- avoid implying more authority, completeness, recency, or certainty than the evidence supports

## 5. Customer Decision Authority — Approved Principle

The following principle is approved and governs this Draft Charter:

> Customers own the determination of whether a nonprofit is verified, eligible, approved, denied, requires manual review, or has insufficient data for the customer's workflow. VerifyForGood provides source facts, normalized data, provenance, derived signals, evidence, and deterministic execution of customer-selected or customer-defined rules.

VerifyForGood may calculate scores, produce baseline compatibility evaluations, match rules, and return policy results. Those outputs do not independently become the customer's final legal, compliance, grant, procurement, donation, or operational decision.

## 6. Evidence and Provenance Principles

1. **Evidence before outcome** — material decisions should be explainable from inspectable evidence.
2. **Facts and interpretations remain distinct** — source-reported status is not the same as a platform score or customer outcome.
3. **Unknown is not adverse** — not found, unavailable, stale, conflicting, failed, disabled, not offered, and negative evidence remain distinguishable.
4. **Derived outputs identify their basis** — scores, flags, and recommendations should expose source and transformation context.
5. **Policy execution is reproducible** — policy ID, version when supported, matched rules, evidence context, and evaluation time should be recoverable.
6. **Customer authority is not inferred from a field name** — API compatibility labels must be interpreted through the governing decision model.

## 7. Product Boundaries

VerifyForGood may provide:

- U.S. nonprofit discovery and lookup
- source-backed organization and filing records
- normalization and entity comparison
- evidence and provenance views
- deterministic derived signals and scoring
- policy evaluation
- API and portal workflows
- integration and evidence-source configuration
- monitoring or refresh workflows where implemented and accurately documented

Implementation status must be verified from current merged code and tests.

## 8. Explicit Non-Goals

VerifyForGood does not independently provide:

- legal advice or legal conclusions
- tax advice or a definitive tax-status opinion beyond attributed source facts
- a universal definition of nonprofit verification or eligibility
- a final sanctions disposition
- a fraud determination
- a universal good-standing conclusion
- grant, procurement, funding, or donation suitability
- an assurance that every relevant source is complete, current, or conflict-free
- authority to replace customer policy, customer review, or human judgment

## 9. Current Prototype Proof Goals

The current prototype should demonstrate that:

- source evidence can be collected and normalized into a coherent nonprofit profile
- provenance and freshness can remain visible
- derived signals can be deterministic and explainable
- policy evaluation can remain separate from source facts and baseline signals
- customer-facing API and portal workflows can share stable terminology and contracts
- incomplete or unavailable evidence can produce honest review states
- technical boundaries can evolve without silently changing product meaning

These proof goals do not mean the platform is production-ready, legally authoritative, secure at scale, or suitable for unattended financial or compliance decisions.

## 10. Trust-Language Rules

Public and internal documentation must not imply that:

- an IRS record proves customer eligibility
- a score proves trustworthiness
- a platform flag is a legal or compliance conclusion
- a sanctions signal is a final sanctions disposition
- a policy template is the customer's final decision
- VerifyForGood universally approves or denies an organization

When terms such as `verified`, `eligible`, `approve`, or `deny` describe current API fields, documentation must identify their implemented source and compatibility context.

## 11. Current Implementation Limitations

At the current inspected baseline:

- scoring emits platform-derived `ELIGIBLE` or `INELIGIBLE` values
- the decision engine emits baseline statuses including `approve`, `approve_with_review`, `manual_review`, `deny`, and `insufficient_data`
- a selected named policy is evaluated separately and may override the baseline into `final_recommendation`
- current policy definitions are static platform-provided templates
- organization settings can enable or require certain evidence integrations
- full customer-authored policy persistence, versioning, administration, and final-decision capture are not established as implemented

These are implementation facts and known gaps, not ratification of the current semantic contract as the final target.

## 12. Decision Principles

When choosing between speed and trust clarity:

- preserve the distinction between evidence and outcome
- prefer reversible, compatibility-preserving changes
- record unknown or conflicting states rather than forcing certainty
- stop for human approval before changing verification, eligibility, sanctions, compliance, tax, fraud, funding, or donation semantics
- keep customer-private policy configuration separate from reusable pure evaluation logic
- avoid broad Architecture changes until source truth and contracts are approved

## 13. Authority and Ratification

- Customer decision authority: **Approved principle**
- Mission and broader Charter: **Draft pending project-owner ratification**
- Strategic Outcomes and Initiative portfolio: **Draft pending project-owner ratification**
- Current implementation descriptions: supported by repository evidence at the recorded baseline

Merging this document does not automatically ratify sections marked Draft.

## 14. Review Cadence

Reconcile this Charter when:

- customer decision semantics change
- public verification or compliance claims change
- a new authoritative source or jurisdiction is added
- policy authoring or decision history is implemented
- public API status meanings change
- the project moves from prototype to production-readiness evaluation
- a material source-truth conflict is discovered
