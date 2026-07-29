<!--
LEAP_DOC_METADATA:
  audience: maintainer, agent, contributor
  doc_type: reconciliation-status
  authority: supporting
  applies_to: verifyforgood
END_LEAP_DOC_METADATA
-->

# Existing-Document Reconciliation Status

Status: Incomplete — large root/source documents still require safe bounded edits  
Owner / approver: Project owner  
Last reconciled: 2026-07-28  
Related Initiative: `INIT-009`  
Related Build Unit: `BU-GOV-007`

## Completed Safely

The documentation branch adds non-destructive source-truth, Charter, strategy, Domain, Architecture, Delivery, Build, inventory, gap, drift, stale-source, and migration records. No existing repository path was deleted, moved, or overwritten.

The 2026-07-28 source-truth alignment pass also completed these bounded changes:

| Path | Change | Runtime impact |
|---|---|---|
| `docs/product/plan-catalog.md` | Added proposed human-readable product/package plan catalog source | None |
| `docs/product/plan-catalog.yaml` | Added proposed structured plan-catalog values | None |
| `tests/test_plan_catalog_source_truth.py` | Added validation comparing structured catalog to current backend entitlements and public catalog projection | None |
| `docs/architecture/plan-catalog.md` | Reclassified as supporting runtime/architecture reference and linked to product catalog source | None |
| `docs/00_start_here.md` | Added product catalog to canonical reading order and documentation areas | None |
| `docs/charter/source-of-truth.md` | Added product/package plan source-truth ownership and runtime-projection distinction | None |
| `docs/governance/drift-ledger.md` | Added plan-catalog and entry-point drift records | None |
| `docs/governance/gap-register.md` | Added product/package source-truth and structured-catalog validation gaps | None |
| `docs/governance/migration-map.md` | Mapped old architecture plan catalog to the new product catalog source | None |

## Existing Files Requiring Follow-Up

The approved LHS called for bounded updates to the following existing files:

| Path | Intended bounded change | Current status |
|---|---|---|
| `AGENTS.md` | Add LEAP reading order, update source-truth entry point from `README.md` to `docs/00_start_here.md`, and add product plan-catalog source-truth note | Still pending; large existing file should be patched with local checkout or safe patch tooling to avoid reconstructing unrelated content |
| `README.md` | Link `docs/00_start_here.md` and add concise authority statement | Still pending; large mixed file intentionally not reconstructed or overwritten in connector-only editing |
| `CUSTOMER_README.md` | Clarify evidence, derived signals, policy templates, customer-owned outcomes, and link to product plan catalog for package source truth | Still pending; update should be bounded and preserve the current customer API contract text |
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

### Source-truth entry point

`docs/00_start_here.md` now states the canonical documentation entry point. `AGENTS.md` and `README.md` still need bounded edits so future agents do not continue treating root `README.md` as the source-truth entry point.

## Gate

`BU-GOV-007` remains incomplete until the large existing-file updates are applied through an environment that can safely patch existing files, followed by the full validation sequence. Do not treat the central stale register or product catalog source as a substitute for visible warnings and source-truth notices on the older files themselves.
