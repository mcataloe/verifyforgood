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
Last reconciled: 2026-09-04  
Canonical owner of: Stale, conflicting, superseded, and do-not-use document status  
Related Initiatives: `INIT-009`

| Path | Status | Evidence | Canonical replacement / owner | Permitted use | Disposition |
|---|---|---|---|---|---|
| `CUSTOMER_README copy.md` | Do not use — stale and conflicting; warning applied | Publishes pricing and stronger claims that conflict with `CUSTOMER_README.md` and current source-truth posture; visible warning now points readers to current sources | `CUSTOMER_README.md`, Project Charter, Decision Authority | Historical comparison only | Keep path with warning; later archive/delete decision |
| `docs/implementation/portal-identity-membership-status.md` | Reconciled bounded snapshot | Status now reflects PostgreSQL customer-account persistence and active organization-context behavior; stale DynamoDB/GSI deployment guidance removed | Current code/tests/migrations plus `INIT-004` records | Bounded implementation evidence | Keep current bounded snapshot |
| `docs/implementation/billing-subscription-status.md` | Reconciled bounded snapshot | Current status says `billing track active`, not complete, and explicitly lists remaining hardening work | Current code/tests, billing plan, `INIT-006` | Bounded implementation evidence only | Keep current bounded snapshot |
| `PLAN.md` | Historical | Records completed implementation phases for a bounded ingest change | Current code/tests and future Build Unit history | Historical implementation traceability | Keep path; classify as historical |

## Candidate Rules

A document is added here only with evidence. `Needs reconciliation` is not equivalent to stale. Do not delete, move, or archive files under `INIT-009`. Physical disposition requires replacement source truth, validated links, and explicit approval.
