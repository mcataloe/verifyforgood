<!--
LEAP_DOC_METADATA:
  audience: maintainer, agent, contributor
  doc_type: gap-register
  authority: supporting
  applies_to: verifyforgood
END_LEAP_DOC_METADATA
-->

# VerifyForGood Gap Register

Status: Active supporting record  
Owner / approver: Project owner  
Last reconciled: 2026-09-04  
Canonical owner of: Known documentation, source-truth, and planning gaps  
Related Initiatives: `INIT-001`, `INIT-006`, `INIT-009`

| ID | Gap | Evidence | Material consequence | Owner / next action | Status |
|---|---|---|---|---|---|
| `GAP-001` | No Project Charter at initial Recon | `docs/charter/project-charter.md` now exists as Draft with approved customer decision-authority principle | Document-existence gap is closed; ratification remains separate | Charter owner / project owner | Resolved as document-existence gap |
| `GAP-002` | No Strategic Outcome registry at initial Recon | Current strategy docs now include Strategic Outcome records | Document-existence gap is closed; strategy remains Draft where marked | Project owner | Resolved as document-existence gap |
| `GAP-003` | No Initiative registry at initial Recon | `docs/strategy/initiative-registry.md` now exists | Work can trace to Initiative records; reconciliation status remains per Initiative | Project owner | Resolved as document-existence gap |
| `GAP-004` | No Roadmap at initial Recon | Current strategy/governance documentation includes Roadmap ownership separate from TODO/backlog | Timing/priority has a defined owner; ratification/freshness remains separate | Project owner | Resolved as document-existence gap |
| `GAP-005` | No Domain map at initial Recon | `docs/domains/domain-map.md` now exists | Persistent responsibility boundaries have a defined source | Project owner | Resolved as document-existence gap |
| `GAP-006` | Customer decision authority not documented | Charter and Decision Authority now explicitly state customer decision ownership | Documentation gap is closed; runtime compatibility labels remain | `INIT-001` for runtime/contract follow-up | Resolved as documentation gap |
| `GAP-007` | Platform emits `ELIGIBLE` / `INELIGIBLE` | Current scoring implementation | Intermediate compatibility output may appear authoritative | Document now; contract Recon under `INIT-001` | Requires Decision |
| `GAP-008` | Platform emits approve/deny baseline decisions | Current decision engine | Baseline evaluation may be confused with customer decision | Document now; compatibility strategy under `INIT-001` | Requires Decision |
| `GAP-009` | Customer policy is an overlay | Verification service evaluates policy after baseline decision | Customer authority is not structurally primary in current contract | Focused Recon under `INIT-001` | Requires Decision |
| `GAP-010` | Policies are static templates | Policy definitions are committed configuration | Fully customer-authored policy management is not implemented | Define scope/versioning under `INIT-001` | Open |
| `GAP-011` | Organization settings require evidence but do not define full policy | Integration settings support enabled/required-for-evaluation | Evidence configuration is only part of customer rule ownership | Future policy contract | Open |
| `GAP-012` | Policy ownership boundary is incomplete | Historical split assumptions and current policy seams do not fully distinguish pure evaluator from customer-private policy state | Pure evaluator and tenant policy configuration need distinct ownership | Future ADR and Recon | Requires Decision |
| `GAP-013` | Root README owned too many truths at initial Recon | Root `README.md` now contains a Documentation Authority notice pointing to `docs/00_start_here.md`, source-truth precedence, Decision Authority, and product catalog sources | Readers now have an explicit canonical-navigation boundary; stale mixed historical/current content remains supporting only | Maintain authority notice; reconcile individual stale implementation claims only in separately bounded work | Resolved for source-truth ownership |
| `GAP-014` | Duplicate customer documentation conflicts | `CUSTOMER_README copy.md` differs on prices and claims, but now carries a visible do-not-use warning | Current readers are directed away from stale claims | Keep warning; later disposition only if separately approved | Resolved for discoverability |
| `GAP-015` | Status documents overstate or mismatch scope | Portal identity status was corrected; billing status already uses bounded `billing track active` wording | High-confidence status mismatch addressed | Maintain bounded status snapshots against repo reality | Resolved for recorded BU-GOV-007 cases |
| `GAP-016` | Historical Phase mapping is incomplete | Phase labels span policy, ingest, billing, frontend, and admin work | Mechanical migration would erase meaning | Continue evidence-based classification as needed | Open |
| `GAP-017` | Local-worktree evidence was unavailable during initial Recon | GitHub connector inspected remote repository only | Uncommitted or local-only work cannot be ruled out by connector-only validation | Require local preflight before implementation work that depends on uncommitted state | Acknowledged; not an INIT-009 documentation blocker |
| `GAP-018` | No stale/do-not-use register at initial Recon | `docs/governance/stale-document-register.md` exists and is active | Central lifecycle record now exists | Maintain register | Resolved as document-existence gap |
| `GAP-019` | No documentation migration map at initial Recon | `docs/governance/migration-map.md` exists and was refreshed against current paths | Semantic migration ownership now exists | Maintain map | Resolved as document-existence gap |
| `GAP-020` | No Delivery/Build registry at initial Recon | `docs/delivery/` and `docs/build-units/` now exist | Bounded planning records now exist | Maintain registries | Resolved as document-existence gap |
| `GAP-021` | Product/package plan source truth needed ratification | Plan/package meaning was backend-code-owned with an architecture snapshot rather than product-owned docs | Humans and agents could treat package meaning as implementation-only and miss product governance | Ratify `docs/product/plan-catalog.md` and `docs/product/plan-catalog.yaml`; then update runtime projection in a separate Build Unit if approved | Requires Decision |
| `GAP-022` | Runtime billing code does not load or generate from structured catalog | `service.py` and `catalog.py` still define/project plan values directly | Structured catalog can drift from runtime unless tests run and future changes follow the catalog-first rule | Keep `tests/test_plan_catalog_source_truth.py`; consider a later implementation Build Unit to load/generate runtime projection from the catalog | Open |
| `GAP-023` | Large root/source-truth files needed bounded reconciliation | `AGENTS.md`, `README.md`, and `TODO.md` were patched on 2026-09-04: AGENTS now uses the canonical docs entry point/current backend topology, README carries its authority notice, and TODO is explicitly backlog-only | The recorded root-file blocker to `BU-GOV-007` is removed | Maintain the bounded notices and current topology during future reconciliations | Resolved |

## Rules

- Do not close a gap solely because a Draft or Proposed document was created unless the gap is specifically document existence/discoverability; ratification and semantic decisions remain separate.
- Mark a gap resolved only when its replacement source exists, status is accurate, and required validation for that gap has passed or the remaining limitation is explicitly separated.
- Trust-sensitive or contract-sensitive gaps remain open or `Requires Decision` until the project owner approves the governing semantics.
