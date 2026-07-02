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
Last reconciled: 2026-07-02  
Canonical owner of: Known documentation, source-truth, and planning gaps  
Related Initiatives: `INIT-001`, `INIT-009`

| ID | Gap | Evidence | Material consequence | Owner / next action | Status |
|---|---|---|---|---|---|
| `GAP-001` | No Project Charter | No Charter entry point existed on inspected `main` | Mission and boundaries can be inferred inconsistently | `BU-GOV-003` | Open |
| `GAP-002` | No Strategic Outcome registry | No stable SO records found | Features cannot trace reliably to desired change | `BU-GOV-004` | Open |
| `GAP-003` | No Initiative registry | Historical Phases and plans carry mixed meanings | Work ownership and completion status are ambiguous | `BU-GOV-004` | Open |
| `GAP-004` | No Roadmap | `TODO.md` and Phase history are used as informal planning | Timing, priority, and identity are conflated | `BU-GOV-004` | Open |
| `GAP-005` | No Domain map | Persistent responsibilities appear in package and service-area docs only | Domains may be mistaken for Initiatives or architecture tiers | `BU-GOV-005` | Open |
| `GAP-006` | Customer decision authority not documented | Code exposes platform baseline labels and a policy overlay | Customers may mistake platform output for a universal determination | `BU-GOV-003`; future `INIT-001` | Open |
| `GAP-007` | Platform emits `ELIGIBLE` / `INELIGIBLE` | Current scoring implementation | Intermediate compatibility output may appear authoritative | Document now; contract Recon under `INIT-001` | Requires Decision |
| `GAP-008` | Platform emits approve/deny baseline decisions | Current decision engine | Baseline evaluation may be confused with customer decision | Document now; compatibility strategy under `INIT-001` | Requires Decision |
| `GAP-009` | Customer policy is an overlay | Verification service evaluates policy after baseline decision | Customer authority is not structurally primary in current contract | Focused Recon under `INIT-001` | Requires Decision |
| `GAP-010` | Policies are static templates | Policy definitions are committed configuration | Fully customer-authored policy management is not implemented | Define scope/versioning under `INIT-001` | Open |
| `GAP-011` | Organization settings require evidence but do not define full policy | Integration settings support enabled/required-for-evaluation | Evidence configuration is only part of customer rule ownership | Future policy contract | Open |
| `GAP-012` | Policy ownership boundary is incomplete | Split docs broadly classify policy/decision as public-core | Pure evaluator and tenant policy configuration need distinct ownership | Future ADR and Recon | Requires Decision |
| `GAP-013` | Root README owns too many truths | README combines architecture, API, operations, Phase history, and product copy | Stale details can compete with canonical docs | Add navigation and ownership notice | Open |
| `GAP-014` | Duplicate customer documentation conflicts | `CUSTOMER_README copy.md` differs on prices and claims | User-trust and pricing confusion | Mark do not use; later disposition | Open |
| `GAP-015` | Status documents overstate or mismatch scope | Identity and billing status files conflict with plans/content | Agents may report inaccurate completion | Reconcile high-confidence cases | Open |
| `GAP-016` | Historical Phase mapping is absent | Phase labels span policy, ingest, billing, frontend, and admin work | Mechanical migration would erase meaning | `BU-GOV-006` | Open |
| `GAP-017` | Local-worktree evidence was unavailable during Recon | GitHub connector inspected remote repository only | Uncommitted or local-only work cannot be ruled out remotely | Local execution preflight | Acknowledged |
| `GAP-018` | No stale/do-not-use register | Conflicting docs lack a central lifecycle record | Stale sources can compete with current truth | `BU-GOV-002` | Open |
| `GAP-019` | No documentation migration map | Existing paths have no canonical destination record | Reorganization could break traceability or tests | `BU-GOV-002` | Open |
| `GAP-020` | No Delivery/Build registry | Plans and Phases are not bounded consistently | Implementation agents may invent scope | `BU-GOV-006` | Open |

## Rules

- Do not close a gap solely because a Draft document was created.
- Mark a gap resolved only when its replacement source exists, status is accurate, and required validation passes.
- Trust-sensitive or contract-sensitive gaps remain open or `Requires Decision` until the project owner approves the governing semantics.
