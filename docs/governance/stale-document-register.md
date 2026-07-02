<!--
LEAP_DOC_METADATA:
  audience: maintainer, agent, contributor
  doc_type: stale-document-register
  authority: supporting
  applies_to: verifyforgood
END_LEAP_DOC_METADATA
-->

# VerifyForGood Stale and Do-Not-Use Register

Status: Active supporting record  
Owner / approver: Project owner  
Last reconciled: 2026-07-02  
Canonical owner of: Stale, conflicting, superseded, and do-not-use document status  
Related Initiatives: `INIT-009`

| Path | Status | Evidence | Canonical replacement / owner | Permitted use | Disposition |
|---|---|---|---|---|---|
| `CUSTOMER_README copy.md` | Do not use — stale and conflicting | Publishes pricing and stronger claims that conflict with `CUSTOMER_README.md` and current source-truth posture | `CUSTOMER_README.md`, Project Charter, Decision Authority | Historical comparison only | Keep path; add warning; later archive/delete decision |
| `docs/implementation/portal-identity-membership-status.md` | Needs reconciliation | Heading/scope concern identity and membership while status wording refers to customer support experience | Current code/tests plus `INIT-004` records | Evidence after verifying individual claims | Keep; flag/correct high-confidence mismatch |
| `docs/implementation/billing-subscription-status.md` | Needs reconciliation | Broad completion statement conflicts with unresolved production decisions in billing plan | Current code/tests, billing plan, `INIT-006` | Bounded implementation evidence only | Keep; qualify completion |
| `PLAN.md` | Historical | Records completed implementation phases for a bounded ingest change | Current code/tests and future Build Unit history | Historical implementation traceability | Keep path; classify as historical |

## Candidate Rules

A document is added here only with evidence. `Needs reconciliation` is not equivalent to stale. Do not delete, move, or archive files under `INIT-009`. Physical disposition requires replacement source truth, validated links, and explicit approval.
