<!--
LEAP_DOC_METADATA:
  audience: maintainer, agent, contributor
  doc_type: reconciliation-status
  authority: supporting
  applies_to: verifyforgood
END_LEAP_DOC_METADATA
-->

# Existing-Document Reconciliation Status

Status: Incomplete — large root documents still require safe bounded edits  
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
| `CUSTOMER_README.md` | Added project documentation source-truth pointers and plan-catalog authority guidance while preserving current customer API behavior | None |

## Existing Files Requiring Follow-Up

The approved LHS called for bounded updates to the following existing files:

| Path | Intended bounded change | Current status |
|---|---|---|
| `AGENTS.md` | Add LEAP reading order, update source-truth entry point from `README.md` to `docs/00_start_here.md`, and add product plan-catalog source-truth note | Still pending; large existing file should be patched with local checkout or safe patch tooling to avoid reconstructing unrelated content |
| `README.md` | Link `docs/00_start_here.md` and add concise authority statement | Still pending; large mixed file intentionally not reconstructed or overwritten in connector-only editing |
| `CUSTOMER_README copy.md` | Add visible do-not-use warning while preserving historical content | Recorded in stale register; file itself not changed |
| `TODO.md` | State that it is a backlog rather than strategy/Roadmap source truth | Not applied; large mixed file intentionally preserved |
| `docs/contributor-naming-rules.md` | Replace local machine links with repository-relative links | Not applied; exact fix is recorded below |
| `docs/repo-target-architecture.md` | Add unresolved customer-policy ownership boundary note | Covered in Architecture index; original file not changed |
| `docs/implementation/portal-identity-membership-status.md` | Remove unrelated customer-support wording and mark Needs Reconciliation | Recorded in inventory/stale register; original file not changed |
| `docs/implementation/billing-subscription-status.md` | Qualify “billing track complete” as a bounded prototype track | Recorded in inventory/stale register; original file not changed |

## Exact Safe Root-Document Edits Pending

Apply these with a local checkout or safe patch tooling rather than reconstructing the large files through connector-only replacement.

### `AGENTS.md`

In the repository section baseline table, replace:

```text
| Current source-truth entry point | `README.md` |
```

with:

```text
| Current source-truth entry point | `docs/00_start_here.md`; root `README.md` remains a supporting compatibility overview |
```

In `Primary source-truth documents`, add `docs/00_start_here.md`, `docs/charter/source-of-truth.md`, `docs/charter/decision-authority.md`, and `docs/product/plan-catalog.md` before `README.md`, and reclassify `README.md` as supporting overview rather than the owner of all project truth.

In `Project Source of Truth`, align the order with `docs/charter/source-of-truth.md`: explicit user/project-owner decisions and ratified governing documents; current code/tests/contracts for implemented behavior; `AGENTS.md`; current canonical docs; then supporting/historical docs.

### `README.md`

Add a short authority notice near the top:

```text
## Documentation Authority

Start with `docs/00_start_here.md` for current project documentation navigation. This root README is a supporting repository overview and compatibility entry point, not the owner of all project truth.

For source-truth precedence, see `docs/charter/source-of-truth.md`. For customer decision-authority rules, see `docs/charter/decision-authority.md`. For product/package plan meaning, see `docs/product/plan-catalog.md` and exact structured values in `docs/product/plan-catalog.yaml`.

For questions about what the software currently does, inspect current merged code, tests, schemas, routes, infrastructure configuration, and public contracts. Documentation must distinguish implemented behavior from proposed or draft intent.
```

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

`BU-GOV-007` remains incomplete until the large root-document updates are applied through an environment that can safely patch existing files, followed by the full validation sequence. Do not treat the central stale register or product catalog source as a substitute for visible source-truth notices on the older files themselves.
