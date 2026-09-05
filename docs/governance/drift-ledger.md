<!--
LEAP_DOC_METADATA:
  audience: maintainer, agent, contributor
  doc_type: drift-ledger
  authority: supporting
  applies_to: verifyforgood
END_LEAP_DOC_METADATA
-->

# VerifyForGood Drift Ledger

Status: Active supporting record  
Owner / approver: Project owner  
Last reconciled: 2026-09-04  
Canonical owner of: Detected differences between source truth, documentation, and repository reality  
Related Initiatives: `INIT-001`, `INIT-006`, `INIT-009`

## Status Vocabulary

- Open
- Acknowledged
- Resolved
- Deferred
- Superseded
- Requires Decision

## Initial Drift

| ID | Finding | Evidence | Status | Planned resolution | Resolving commit | Remaining risk |
|---|---|---|---|---|---|---|
| `DRIFT-001` | No Project Charter at initial Recon | Initial inspected baseline lacked a Charter; `docs/charter/project-charter.md` now exists as Draft with approved customer decision-authority principle | Resolved as document-existence drift | `BU-GOV-003` | Historical governance commits | Charter ratification remains separate |
| `DRIFT-002` | No Strategic Outcome or Initiative registry at initial Recon | Strategy registry now exists under `docs/strategy/` | Resolved as document-existence drift | `BU-GOV-004` | Historical governance commits | Draft strategy ratification/reconciliation remains separate |
| `DRIFT-003` | Customer decision authority was not explicit | Decision Authority and Charter now explicitly state customer decision ownership | Resolved as documentation drift | `BU-GOV-003` | Historical governance commits | Runtime compatibility labels remain under `INIT-001` |
| `DRIFT-004` | Scoring emits platform-owned `ELIGIBLE/INELIGIBLE` labels | Current scoring calculator | Requires Decision | Document as baseline compatibility output; future `INIT-001` Recon | Pending | API consumers may treat as final |
| `DRIFT-005` | Decision engine emits approve/deny labels | Current decision engine | Requires Decision | Document authority matrix; future compatibility strategy | Pending | User-trust and contract risk |
| `DRIFT-006` | Customer policy is an overlay | Policy evaluation follows baseline decision | Requires Decision | Record current reality; future semantic redesign decision | Pending | Customer authority is not structurally primary |
| `DRIFT-007` | Customer policies are static | Policy definitions live in source configuration | Open | State limitation; define future policy Initiative | Pending | No customer policy authoring/versioning |
| `DRIFT-008` | Organization settings can require evidence but not define full policies | Integration settings service and models | Open | Distinguish evidence configuration from policy ownership | Pending | Partial customer control may be overstated |
| `DRIFT-009` | Policy definitions and pure evaluator are not architecturally separated | Historical split assumptions plus current policy seams | Requires Decision | Current Architecture index records unresolved boundary; future ADR under `INIT-001` | Pending | Incorrect public/private extraction boundary if moved without decision |
| `DRIFT-010` | Root README owned too many truth categories without an authority boundary | Root `README.md` now contains a Documentation Authority notice that directs readers to canonical project/source-truth documents | Resolved for source-truth ownership | Keep README as supporting compatibility overview | `5d206f8ba20b807adef110b5c46a6172e9b4d704` | README still contains mixed historical/current implementation detail; reconcile individual claims only in separately bounded work |
| `DRIFT-011` | Duplicate customer documentation conflicts | `CUSTOMER_README copy.md` differs on prices and stronger claims | Resolved for discoverability | Visible do-not-use warning added; keep historical copy | `e2b3cbcdac5005854490a7abf08fd7e89c39efd3` | Later archive/delete decision remains separate |
| `DRIFT-012` | Marketing terminology may overstate authority | Marketing copy uses compliance-grade verification wording | Deferred | Record under `INIT-001`; no frontend changes in `INIT-009` | Pending | Public user-trust risk remains |
| `DRIFT-013` | Identity status document contained unrelated status wording and stale DynamoDB guidance | Portal identity status file reconciled to current PostgreSQL/organization-context snapshot | Resolved | Correct bounded status and remove stale persistence deployment guidance | `71f1bd93d0d56a84afb7db812d7cc1be8e2d958b` | Future identity changes still require `INIT-004` Recon as appropriate |
| `DRIFT-014` | Billing completion wording conflicted with deferred decisions | Current billing status now says `billing track active` and lists remaining hardening work | Resolved | Preserve bounded active-status wording | Verified 2026-09-04 | Production billing readiness remains a separate product/operations question |
| `DRIFT-015` | Historical Phase records lack Initiative traceability | README, plans, and commit-era labels | Open | Add semantic migration map and refine mappings as evidence supports | Pending | Some mappings remain ambiguous |
| `DRIFT-016` | Local worktree was unavailable during initial Recon | Connector-only repository inspection cannot see uncommitted local work | Acknowledged | Require local preflight before implementation when uncommitted state matters | N/A | Not an INIT-009 documentation blocker |
| `DRIFT-017` | Contributor naming doc contained local filesystem links | `docs/contributor-naming-rules.md` is no longer present on current `main`; current Architecture index no longer links it as an active source | Superseded | Record removed historical path; do not recreate solely to repair old links | `457d64b5f9a2e0f8115a94a29a656cad6ae9c7c2` | Historical references may remain outside current active source truth |
| `DRIFT-018` | ADRs lacked a consolidated status index | `docs/architecture/README.md` exists and was refreshed against current paths | Resolved | Maintain Architecture index against current repo reality | `457d64b5f9a2e0f8115a94a29a656cad6ae9c7c2` | Individual ADR authority/ratification remains separate |
| `DRIFT-019` | Source-truth entry point conflict | `AGENTS.md` now records `docs/00_start_here.md` as the canonical documentation entry point; README is explicitly supporting; TODO is backlog-only | Resolved | Maintain aligned root notices and source-truth precedence | `890878ff59f1bd50a98b040d910c0f360c398a1f`, `5d206f8ba20b807adef110b5c46a6172e9b4d704`, `3c6d76802a12a9f9ffcf14e4cfd07b1ea7c51d22` | Future source-truth changes must update all affected entry points deliberately |
| `DRIFT-020` | Plan catalog was code-owned despite desired document-owned package governance | `docs/architecture/plan-catalog.md` previously said code and `/v1/plans` were authoritative for implemented plan values | Acknowledged | Added `docs/product/plan-catalog.md`, `docs/product/plan-catalog.yaml`, and reclassified architecture plan catalog as runtime reference | Pending | Runtime still reads code, not the structured catalog |
| `DRIFT-021` | Plan package behavior was split across plan catalog, customer docs, code, and tests | Aliases, trial behavior, route mapping, overage policy, and fallback behavior were not all in the old plan catalog reference | Acknowledged | Consolidated the package model in `docs/product/plan-catalog.md` and `docs/product/plan-catalog.yaml` | Pending | Product catalog ratification/runtime projection remain separate |
| `DRIFT-022` | Plan-catalog tests validated backend catalog from code, not documentation/catalog authority | `tests/test_billing_domain.py` asserted runtime payload matches `DEFAULT_ENTITLEMENTS` | Acknowledged | Added `tests/test_plan_catalog_source_truth.py` to validate the structured catalog against code and runtime projection | Pending | Test execution remains a separate CI/local validation concern |

## Update Rule

Every Build Unit that changes a listed condition must update this ledger with the changed paths, commit SHA when known, and remaining risk. A documentation change does not resolve runtime or contract drift unless the relevant implementation and validation have also changed under a separately approved Initiative.
