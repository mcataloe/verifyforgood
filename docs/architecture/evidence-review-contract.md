# Evidence Review Contract

## Purpose

The canonical customer-facing nonprofit review contract is the top-level
`review` object. It reports source facts, evidence conditions, source coverage,
and customer-owned requirements evaluation without making a universal
VerifyForGood funding, donation, grant, legal, or compliance decision.

Legacy `scores`, `decision`, `policy_evaluation`, and `final_recommendation`
fields remain available for compatibility during the transition, but new portal
behavior should use `review` when the backend returns it.

## Envelope

`review.contract_version` is currently `1.0`.

The envelope contains:

- `evidence_review`: source checks, issues, source coverage, and aggregate
  evidence condition.
- `requirements_evaluation`: optional customer-owned requirement results when
  a customer policy is supplied.
- `customer_decision`: currently `null`; customer decision persistence is a
  future workflow.

The contract is additive. Routes, response envelopes, status codes, and legacy
fields are preserved.

## Evidence Review

Allowed `evidence_review.status` values:

- `complete`
- `incomplete`
- `stale`
- `conflicting`
- `source_unavailable`
- `review_required`

Evidence status is derived from source checks and issues only. It must not be
derived from legacy `overall`, `trust`, `compliance`, eligibility, `decision`,
`policy_evaluation`, or `final_recommendation` values.

Checks may cover:

- IRS exempt organization status and deductibility source facts.
- Form 990 filing recency and parse status evidence.
- EIN/name match evidence.
- Checked state registration status and flags.
- External source availability and potential-match signals.
- Integration coverage and required-source availability.

Source limitations must remain visible where they affect interpretation. For
example, missing or stale Form 990 evidence is not a complete legal
filing-obligation determination, and no-match supplemental provider data is not
a clearance.

## Customer Requirements

`requirements_evaluation` is separate from the legacy approval-style policy
engine. It represents customer-authored requirements, not VerifyForGood policy.

Allowed aggregate results:

- `requirements_met`
- `requirements_not_met`
- `unresolved`
- `unable_to_evaluate`

Allowed per-requirement results:

- `met`
- `not_met`
- `unresolved`
- `not_applicable`

The evaluation includes policy metadata such as policy ID, version, owner,
effective timestamp, and adoption status. Requirement failures do not create a
VerifyForGood grant, funding, or approval decision.

## Entitlements

Plans may hide premium legacy scoring, benchmarking, source, or detail fields,
but visible requirements results must retain the minimum explanatory evidence:
the relevant check IDs, check statuses, source coverage, issues, and limitation
text needed to understand the result.

## Portal Semantics

The portal should not infer `verified` from active IRS status. It should show
`IRS status: Active` as a source fact and show evidence-review or customer
requirements sections only when the backend returns `review`.

Search summaries should remain source-fact summaries unless a backend review
envelope is present. Detail views may show review badges based on
`evidence_review.status`.

## Compatibility

During transition:

- `scores`, `decision`, `policy_evaluation`, and `final_recommendation` remain
  compatibility fields.
- Existing `/v1/...` routes and response envelopes remain stable.
- Cached profiles without `review` may compute it on read or overlay when
  enough source facts are present.
- No database migration or cache backfill is required for version `1.0`.
