<!--
LEAP_DOC_METADATA:
  audience: user, maintainer, agent, contributor
  doc_type: decision-authority
  authority: approved-principle
  applies_to: verifyforgood
END_LEAP_DOC_METADATA
-->

# VerifyForGood Decision Authority

Status: Approved principle; implementation reconciliation required  
Owner / approver: Project owner  
Last reconciled: 2026-07-02  
Canonical owner of: Separation of platform evidence and customer-owned determinations  
Related Strategic Outcomes: `SO-001`, `SO-002`, `SO-003`, `SO-004`, `SO-005`, `SO-007`  
Related Initiatives: `INIT-001`, `INIT-002`, `INIT-005`, `INIT-009`

## Governing Decision

Customers own the determination of whether a nonprofit is verified, eligible, approved, denied, requires manual review, or has insufficient data for the customer's workflow.

VerifyForGood provides:

- attributed source facts
- normalized data
- provenance and freshness context
- derived signals and scores
- evidence completeness and conflict indicators
- deterministic execution of customer-selected or customer-defined rules
- explainable policy results

VerifyForGood does not independently own the customer's final operational, legal, tax, sanctions, compliance, fraud, grant, procurement, funding, or donation-suitability decision.

## Authority Matrix

| Output class | Example | Produced by | Meaning | Customer authority | Allowed use | Prohibited interpretation |
|---|---|---|---|---|---|---|
| Source fact | IRS active status, filing date | Source adapter with attribution | Condition reported by a named source for a period or retrieval time | Customer may use as evidence | Evidence display, filtering, policy input | Universal customer eligibility or legal conclusion |
| Normalized fact | Normalized EIN or filing field | VerifyForGood normalization | Standardized representation of source data | Customer interprets through its policy | Comparison, joins, evaluation | Independent truth beyond the cited source |
| Evidence state | Missing, stale, conflicting, unavailable | VerifyForGood evidence processing | Availability, freshness, or consistency condition | Customer decides materiality | Review routing and policy input | Adverse finding without supporting evidence |
| Derived signal | Overall, trust, transparency, compliance-named, or financial score | VerifyForGood deterministic calculation | Transparent indicator derived from identified factors | Customer chooses relevance and thresholds | Policy input, prioritization, explanation | Objective trustworthiness, compliance, or suitability |
| Baseline evaluation | Current `decision.status` or `score_explanation.eligibility` | VerifyForGood prototype compatibility logic | Platform-generated intermediate or fallback evaluation under current rules | Not the final customer determination | Compatibility, policy input, review aid | Universal approval, denial, eligibility, or legal conclusion |
| Policy result | `policy_evaluation.final_recommendation` / top-level `final_recommendation` | Deterministic evaluator applying a selected policy | Result of the rules that were applied to the evidence and signals | Customer owns selection, interpretation, and workflow use | Workflow recommendation and automation within approved customer policy | VerifyForGood's independent legal or compliance decision |
| Customer determination | Customer's verified, eligible, approved, denied, review, or insufficient-data outcome | Customer or customer-authorized workflow | Customer-owned operational decision under its rules and accountability | Final customer authority | Customer workflow, subject to its governance | Independent VerifyForGood determination |

## Required Separation

Documentation, APIs, interfaces, and future storage should distinguish:

```text
Source systems
    ↓
Attributed source facts
    ↓
Normalized facts and provenance
    ↓
VerifyForGood-derived signals
    ↓
Customer-selected or customer-defined policy
    ↓
Policy evaluation
    ↓
Customer determination
```

Do not collapse these layers into one ambiguous `verified` or `eligible` state.

## Current Contract Reality

The current implementation includes compatibility-era fields whose names can sound authoritative:

- `score_explanation.eligibility`
- `decision.status`
- `summary.eligibility_status`
- `policy_evaluation`
- `final_recommendation`

The current verification flow builds scores and a baseline decision, then evaluates the selected named policy. A policy may override the baseline recommendation. Current named policies are static platform-provided definitions, while organization settings can control enabled and required evidence integrations.

This document does not change those API fields or runtime behavior. Contract changes require a separate `INIT-001` Recon, compatibility plan, migration posture, tests, and approval.

## Terminology Rules

### Verified

Use only with an explicit subject and rule context, for example:

- source record verified as retrieved from a named source
- identity match verified under a defined comparison rule
- customer marked the nonprofit verified under policy version X

Do not use `verified nonprofit` as an unsupported universal platform conclusion.

### Eligible / Ineligible

Eligibility is customer- and workflow-specific unless the text refers narrowly to a named source condition or current API compatibility field. Identify the governing policy, evidence, and time.

### Approved / Denied

Approval and denial are customer workflow outcomes. Current baseline `decision.status` values must be described as platform-generated evaluations, not customer determinations.

### Manual Review / Insufficient Data

These should remain distinct:

- manual review means an applicable rule or evidence condition requires human/customer review
- insufficient data means required evidence is not available or adequate for the applicable evaluation

Neither state should be silently converted into approval or denial.

## Unknown and Conflict States

Keep these meanings distinct:

- not found
- unknown
- unavailable
- stale
- conflicting
- failed
- not offered
- disabled
- not required
- adverse or negative evidence

Data presence is not proof of suitability, and data absence is not proof of ineligibility.

## Policy Explainability

A policy evaluation should be explainable from:

- customer/account/workspace context as applicable
- policy ID
- policy version when versioning exists
- effective policy scope and precedence
- evidence snapshot or references
- derived-signal model/version context
- matched rule IDs and descriptions
- evaluation time
- policy result
- final customer action when separately recorded

Several of these capabilities remain future `INIT-001` work and must not be documented as implemented until repository evidence exists.

## Public Claims

Product and marketing copy may describe evidence-backed nonprofit review, deterministic signals, explainable policy execution, and customer-controlled workflows. It must not imply that VerifyForGood provides an independent legal, tax, sanctions, fraud, compliance, grant, procurement, funding, or donation-suitability conclusion.

## Required Future Work

`INIT-001` must resolve:

- customer policy authoring versus configurable templates
- scope and precedence
- versioning and immutability
- authorization and ownership
- evidence snapshot requirements
- final customer-decision capture
- API compatibility for current baseline labels
- public-core versus private-platform ownership
- public terminology and migration

Until those decisions are approved, current runtime behavior remains unchanged and documented as current reality rather than final product intent.
