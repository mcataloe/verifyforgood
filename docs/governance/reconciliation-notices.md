<!--
LEAP_DOC_METADATA:
  audience: maintainer, agent, contributor
  doc_type: reconciliation-status
  authority: supporting
  applies_to: verifyforgood
END_LEAP_DOC_METADATA
-->

# Existing-Document Reconciliation Status

Status: Incomplete — safe update action unavailable in this execution environment  
Owner / approver: Project owner  
Last reconciled: 2026-07-02  
Related Initiative: `INIT-009`  
Related Build Unit: `BU-GOV-007`

## Completed Safely

The documentation branch adds non-destructive source-truth, Charter, strategy, Domain, Architecture, Delivery, Build, inventory, gap, drift, stale-source, and migration records. No existing repository path was deleted, moved, or overwritten.

## Existing Files Requiring Follow-Up

The approved LHS called for bounded updates to the following existing files:

| Path | Intended bounded change | Current status |
|---|---|---|
| `AGENTS.md` | Add LEAP reading order and customer-decision authority rule | Not applied; existing-file replacement blocked by connector safety control |
| `README.md` | Link `docs/00_start_here.md` and add concise authority statement | Not applied; large mixed file intentionally not reconstructed or overwritten |
| `CUSTOMER_README.md` | Clarify evidence, derived signals, policy templates, and customer-owned outcomes | Not applied; existing-file replacement blocked |
| `CUSTOMER_README copy.md` | Add visible do-not-use warning while preserving historical content | Recorded in stale register; file itself not changed |
| `TODO.md` | State that it is a backlog rather than strategy/Roadmap source truth | Not applied; large mixed file intentionally preserved |
| `docs/contributor-naming-rules.md` | Replace local machine links with repository-relative links | Not applied; exact fix is recorded below |
| `docs/repo-target-architecture.md` | Add unresolved customer-policy ownership boundary note | Covered in Architecture index; original file not changed |
| `docs/implementation/portal-identity-membership-status.md` | Remove unrelated customer-support wording and mark Needs Reconciliation | Recorded in inventory/stale register; original file not changed |
| `docs/implementation/billing-subscription-status.md` | Qualify “billing track complete” as a bounded prototype track | Recorded in inventory/stale register; original file not changed |

## Exact Safe Link Repairs Pending

In `docs/contributor-naming-rules.md`, replace:

- `/c:/Repos/charity-status-api/docs/capability-naming-abstraction.md` with `capability-naming-abstraction.md`
- `/c:/Repos/charity-status-api/docs/infrastructure-naming-normalization.md` with `infrastructure-naming-normalization.md`
- `/c:/Repos/charity-status-api/docs/monthly-ingest-architecture.md` with `monthly-ingest-architecture.md`
- `/c:/Repos/charity-status-api/docs/monthly-ingest-runbook.md` with `monthly-ingest-runbook.md`

## Required Status Corrections Pending

### Portal identity status

The phrase `customer support experience implemented` does not match the document title or listed scope. Replace it with an evidence-based identity/membership status or mark the record `Needs Reconciliation` after checking current code and tests.

### Billing subscription status

The phrase `billing track complete` must be bounded. Current documentation supports implemented provider integration, organization billing identity, and subscription lifecycle work, while production policy and operations decisions remain unresolved.

## Gate

`BU-GOV-007` is not complete. These updates should be applied through an environment that can safely edit existing repository files, followed by the full validation sequence. Do not treat the central stale register as a substitute for a visible warning on the stale file itself.
