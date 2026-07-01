# Evidence Review Transition

## Scope

This transition adds the versioned evidence review contract while preserving
legacy scoring, decision, policy, and recommendation fields.

Retargeting note: this work was retargeted to current workspace commit
`cc9bc5b549c264c1815d2b07a6cfa6b30857c0ee`. The older LHS baseline
`694d07e` is now an ancestor, and implementation areas have moved from
`infrastructure/...` into `backend/shared/...` and `backend/customer-api/...`.

Branch: `leap/evidence-review-contract-v1`

## Build Unit Ledger

### BU0: Contract and Characterization

Status: implemented.

- Added architecture contract documentation.
- Added review characterization tests for source status independence from
  legacy scores, decisions, policy output, and recommendations.
- Updated selected legacy tests to import current `verification.backend...`
  package paths.

### BU1: Canonical Review Domain

Status: implemented.

- Added `verification.backend.shared.review`.
- Added `review.contract_version = "1.0"`.
- Added source check, issue, source coverage, and evidence-status builders.
- Kept evidence review status independent from legacy score and decision
  fields.

### BU2: Customer-Owned Requirements

Status: implemented for the initial neutral evaluator.

- Added optional customer requirements evaluation to the review builder.
- Preserved the legacy `policy` package behavior.
- Labeled legacy policy/recommendation output as compatibility behavior in
  docs.

### BU3: API and Entitlements

Status: implemented.

- Added top-level `review` to lookup, verify, cached-profile, and advisory
  detail paths where source facts are available.
- Cached profiles without `review` compute it on read/overlay without a cache
  migration or backfill.
- Free-plan response shaping retains the review envelope and minimum
  explanatory evidence while hiding premium legacy scoring details.

### BU4: Portal/UI Convergence

Status: implemented.

- Portal nonprofit detail and search now treat IRS status as a source fact.
- Detail views show evidence review and customer requirements only from the
  backend `review` envelope.
- Shared status badges now use evidence/review condition labels while retaining
  legacy status values for compatibility.
- Dashboard copy no longer describes active IRS records as verified or cleared
  by the platform.

### BU5: Docs, Examples, Validation

Status: implemented with repository-wide validation limitations.

- Added this ledger and architecture contract.
- Updated customer, frontend, TODO, and Postman documentation.
- Focused backend review, policy, evidence, runtime, serving, and response
  shaping tests pass.
- Review-related portal and shared UI tests pass.
- Full frontend build passes.
- Full Python collection is still blocked by unrelated repository baseline
  issues: remaining legacy `infrastructure.verification` imports and missing
  `zipfile64` in Form 990 ingest tests.
- Full frontend format, lint, test, and typecheck commands are still blocked by
  unrelated workspace baseline issues outside this transition.

## Rollback Notes

The transition is additive. A rollback can remove `review` from response
shaping and portal rendering without changing stored database schemas or
customer route contracts.

No database migration, new dependency, infrastructure change, auth change,
billing change, API version change, or production deployment is part of this
transition.

## Follow-Up Register

- Decide versioning and retirement timing for legacy `scores`, `decision`,
  `policy_evaluation`, and `final_recommendation` customer fields.
- Design customer policy authoring, adoption, effective dating, and audit
  workflows.
- Design customer decision persistence and audit history.
- Complete legal/source-term review for displayed provider facts and
  limitations.
- Plan rollout communications and compatibility monitoring.
- Add advanced entity resolution for ambiguous names, aliases, and potential
  matches.
