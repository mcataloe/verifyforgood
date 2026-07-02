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
Last reconciled: 2026-07-02  
Canonical owner of: Semantic mapping from legacy and mixed documents to current truth owners  
Related Initiatives: `INIT-009`

Migration is semantic reconciliation, not global renaming. Existing paths remain in place during this Initiative.

| Legacy/current path | Existing meaning | New canonical owner | Path action | Status |
|---|---|---|---|---|
| `README.md` | Mixed overview, API, Architecture, operations, and history | `docs/00_start_here.md` plus specialized current docs | Keep; add canonical link and authority statement | Planned |
| `CUSTOMER_README.md` | Customer API and product overview | Customer guide supported by Charter and Decision Authority | Keep; clarify authority | Planned |
| `CUSTOMER_README copy.md` | Conflicting duplicate customer guide | `CUSTOMER_README.md` | Keep; mark do not use | Planned |
| `TODO.md` | Deferred work list | Initiative registry and Roadmap own strategy; TODO remains backlog | Keep; add ownership notice | Planned |
| `PLAN.md` | Completed bounded ingest implementation | Historical Build Unit evidence under `INIT-003` | Keep; classify historical | Planned |
| `docs/repo-target-architecture.md` | Architecture assessment and split direction | Architecture index and future ADRs | Keep; add unresolved customer-policy boundary note | Planned |
| `docs/form990-ingest-plan.md` | Mixed Architecture, Delivery, Build, status, and history | `INIT-003` delivery/build records plus Architecture docs | Keep; later reconcile | Needs reconciliation |
| `docs/implementation/portal-identity-membership-plan.md` | Implementation plan | `INIT-004` delivery/build records | Keep; link when records exist | Planned |
| `docs/implementation/portal-identity-membership-status.md` | Conflicting status snapshot | Repo reality and `INIT-004` status | Keep; qualify | Planned |
| `docs/implementation/billing-subscription-plan.md` | Billing plan and open decisions | `INIT-006` delivery/build and Architecture records | Keep | Planned |
| `docs/implementation/billing-subscription-status.md` | Overbroad completion snapshot | Repo reality and `INIT-006` status | Keep; qualify | Planned |
| Phase 6B references | Customer policy engine implementation slice | Historical Delivery/Build Unit under `INIT-001` | Preserve label and add mapping | Planned |
| Phase 8B references | Weighting-profile implementation slice | Historical Build Unit spanning `INIT-001` and `INIT-002` | Preserve label and add mapping | Planned |
| Phase 10 references | Form 990 implementation body | Delivery/Build Units under `INIT-003` | Preserve label and add mapping | Planned |
| Phase 12 references | Billing model implementation | Historical Delivery Unit under `INIT-006` | Preserve label and add mapping | Planned |
| Phase 15 references | Frontend and docs work | Delivery Units under `INIT-005` and/or `INIT-008` | Preserve; classify from evidence | Needs reconciliation |
| Phase 20 references | Tenant-aware API work | Delivery Units spanning `INIT-004` and `INIT-005` | Preserve label and add mapping | Planned |
| Phase 21 references | Billing work | Delivery Units under `INIT-006` | Preserve label and add mapping | Planned |
| Phase 22 references | Customer administration | Delivery Units under `INIT-004` and `INIT-005` | Preserve label and add mapping | Planned |
| Step Functions phases | Required operational sequence | Operational process phases | Preserve unchanged | Classified |
| Architecture migration stages | Chronological migration order | Architecture migration phases | Preserve unchanged | Classified |
| Qualified `PlatformLayer` values | Technical structural tier | Architecture Layer | Preserve unchanged | Classified |

## Compatibility Rules

- Preserve LEAP, Layered House Standard, and LEAP LHS names.
- Preserve qualified Architecture Layer terminology.
- Preserve historical Phase IDs and headings.
- Do not move tested or public paths without a separately approved migration and link plan.
- Archive only after replacement source truth exists and links are validated.
