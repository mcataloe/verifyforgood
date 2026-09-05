<!--
LEAP_DOC_METADATA:
  audience: maintainer, agent, contributor
  doc_type: documentation-migration-map
  authority: supporting
  applies_to: verifyforgood
END_LEAP_DOC_METADATA
-->

# VerifyForGood Documentation Migration Map

Status: Active supporting record  
Owner / approver: Project owner  
Last reconciled: 2026-09-04  
Canonical owner of: Semantic mapping from legacy and mixed documents to current truth owners  
Related Initiatives: `INIT-006`, `INIT-009`

Migration is semantic reconciliation, not global renaming. Existing paths should be preserved when present unless a separate approved migration changes them. When an older path is already absent on current `main`, record that fact rather than recreating it without an approved need.

| Legacy/current path | Existing meaning | New canonical owner | Path action | Status |
|---|---|---|---|---|
| `README.md` | Mixed overview, API, Architecture, operations, and history | `docs/00_start_here.md` plus specialized current docs | Keep; canonical link and authority statement added | Applied 2026-09-04 |
| `CUSTOMER_README.md` | Customer API and product overview | Customer guide supported by Charter, Decision Authority, and product catalog | Keep; clarify authority and link product catalog | Applied |
| `CUSTOMER_README copy.md` | Conflicting duplicate customer guide | `CUSTOMER_README.md` | Keep; mark do not use | Applied 2026-09-04 |
| `TODO.md` | Deferred work list | Initiative registry and Roadmap own strategy; TODO remains backlog | Keep; backlog/source-truth ownership notice added | Applied 2026-09-04 |
| `PLAN.md` | Completed bounded ingest implementation | Historical Build Unit evidence under `INIT-003` | Keep; classify historical | Classified |
| `docs/architecture/plan-catalog.md` | Human-readable snapshot of implemented plan catalog values and runtime projection notes | `docs/product/plan-catalog.md` for package meaning; `docs/product/plan-catalog.yaml` for structured values; architecture file remains runtime reference | Keep; reclassify as supporting runtime/architecture reference | Applied |
| `docs/product/plan-catalog.md` | Human-readable product/package plan model | Product/package source after ratification | Keep | Added; pending ratification where marked Draft/Proposed |
| `docs/product/plan-catalog.yaml` | Structured plan catalog values | Exact machine-readable catalog source after ratification | Keep | Added; validation/ratification status governed by product docs |
| `AGENTS.md` | Repository agent routing, project rules, topology, and source-truth navigation | Repository operating instructions aligned to current canonical docs and repo reality | Keep; update source-truth entry, backend topology/commands, and removed-source references | Applied 2026-09-04 |
| `docs/repo-target-architecture.md` | Historical architecture assessment and split direction | Current Architecture index, current backend/frontend READMEs, and active ADRs | Do not recreate solely for compatibility; preserve historical references as migration evidence | Path absent on current `main`; index reconciled 2026-09-04 |
| `docs/contributor-naming-rules.md` | Historical contributor naming guidance | Current repo conventions plus active source-of-truth/Architecture guidance | Do not recreate solely to repair historical local-machine links | Path absent on current `main`; index reconciled 2026-09-04 |
| `docs/form990-ingest-plan.md` | Mixed Architecture, Delivery, Build, status, and history | `INIT-003` delivery/build records plus Architecture docs | Keep; later reconcile | Needs reconciliation |
| `docs/implementation/portal-identity-membership-plan.md` | Implementation plan | `INIT-004` delivery/build records | Keep if present; link when records exist | Planned |
| `docs/implementation/portal-identity-membership-status.md` | Identity/membership status snapshot | Repo reality and `INIT-004` status | Keep; bounded status corrected | Applied 2026-09-04 |
| `docs/implementation/billing-subscription-plan.md` | Billing plan and open decisions | `INIT-006` delivery/build and Architecture records | Keep | Planned |
| `docs/implementation/billing-subscription-status.md` | Billing implementation status snapshot | Repo reality and `INIT-006` status | Keep; bounded as active rather than complete | Applied before 2026-09-04; verified during BU-GOV-007 reconciliation |
| Phase 6B references | Customer policy engine implementation slice | Historical Delivery/Build Unit under `INIT-001` | Preserve label and add mapping | Planned |
| Phase 8B references | Weighting-profile implementation slice | Historical Build Unit spanning `INIT-001` and `INIT-002` | Preserve label and add mapping | Provisional |
| Phase 10 references | Form 990 implementation body | Delivery/Build Units under `INIT-003` | Preserve label and add mapping | Needs detailed reconciliation |
| Phase 12 references | Billing model implementation | Historical Delivery Unit under `INIT-006` | Preserve label and add mapping | Provisional |
| Phase 15 references | Frontend and docs work | Delivery Units under `INIT-005` and/or `INIT-008` | Preserve; classify from evidence | Needs reconciliation |
| Phase 20 references | Tenant-aware API work | Delivery Units spanning `INIT-004` and `INIT-005` | Preserve label and add mapping | Provisional |
| Phase 21 references | Billing work | Delivery Units under `INIT-006` | Preserve label and add mapping | Provisional |
| Phase 22 references | Customer administration | Delivery Units under `INIT-004` and `INIT-005` | Preserve label and add mapping | Provisional |
| Step Functions phases | Required operational sequence | Operational process phases | Preserve unchanged | Classified |
| Architecture migration stages | Chronological migration order | Architecture migration phases | Preserve unchanged | Classified |
| Qualified `PlatformLayer` values | Technical structural tier | Architecture Layer | Preserve unchanged | Classified |

## Compatibility Rules

- Preserve LEAP, Layered House Standard, and LEAP LHS names.
- Preserve qualified Architecture Layer terminology.
- Preserve historical Phase IDs and headings.
- Do not move tested or public paths without a separately approved migration and link plan.
- Do not recreate a removed historical document merely because an older index references it; first establish whether current source truth requires a replacement.
- Archive only after replacement source truth exists and links are validated.
