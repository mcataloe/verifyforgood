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
Last reconciled: 2026-07-02  
Canonical owner of: Detected differences between source truth, documentation, and repository reality  
Related Initiatives: `INIT-001`, `INIT-009`

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
| `DRIFT-001` | No Project Charter | No Charter file on inspected `main` | Open | `BU-GOV-003` | Pending | Ratification still required |
| `DRIFT-002` | No Strategic Outcome or Initiative registry | No canonical strategy files found | Open | `BU-GOV-004` | Pending | Draft status and portfolio reconciliation |
| `DRIFT-003` | Customer decision authority was not explicit | Product docs and APIs use verification/eligibility terminology without a governing authority document | Open | Decision Authority document | Pending | Runtime contracts remain unchanged |
| `DRIFT-004` | Scoring emits platform-owned `ELIGIBLE/INELIGIBLE` labels | Current scoring calculator | Requires Decision | Document as baseline compatibility output; future `INIT-001` Recon | Pending | API consumers may treat as final |
| `DRIFT-005` | Decision engine emits approve/deny labels | Current decision engine | Requires Decision | Document authority matrix; future compatibility strategy | Pending | User-trust and contract risk |
| `DRIFT-006` | Customer policy is an overlay | Policy evaluation follows baseline decision | Requires Decision | Record current reality; future semantic redesign decision | Pending | Customer authority is not structurally primary |
| `DRIFT-007` | Customer policies are static | Policy definitions live in source configuration | Open | State limitation; define future policy Initiative | Pending | No customer policy authoring/versioning |
| `DRIFT-008` | Organization settings can require evidence but not define full policies | Integration settings service and models | Open | Distinguish evidence configuration from policy ownership | Pending | Partial customer control may be overstated |
| `DRIFT-009` | Policy definitions and pure evaluator are not architecturally separated | Repository target architecture and split plan | Requires Decision | Architecture note and future ADR | Pending | Incorrect public/private extraction boundary |
| `DRIFT-010` | Root README owns too many truth categories | Root README content | Open | Add source-truth entry point and bounded authority notice | Pending | Historical and current claims remain mixed |
| `DRIFT-011` | Duplicate customer documentation conflicts | `CUSTOMER_README.md` and copy | Open | Mark copy do not use | Pending | Later archive/delete decision |
| `DRIFT-012` | Marketing terminology may overstate authority | Marketing copy uses compliance-grade verification wording | Deferred | Record under `INIT-001`; no frontend changes in `INIT-009` | Pending | Public user-trust risk remains |
| `DRIFT-013` | Identity status document contains unrelated status wording | Portal identity status file | Open | Correct or flag high-confidence mismatch | Pending | Other status claims may need Recon |
| `DRIFT-014` | Billing completion claim conflicts with deferred decisions | Billing status and plan documents | Open | Qualify bounded completion | Pending | Production readiness unresolved |
| `DRIFT-015` | Historical Phase records lack Initiative traceability | README, plans, and commit-era labels | Open | Add semantic migration map | Pending | Some mappings may remain ambiguous |
| `DRIFT-016` | Local worktree was unavailable during Recon | Remote-only connector inspection | Acknowledged | Require local preflight before implementation | N/A | Remote execution cannot see local-only work |
| `DRIFT-017` | Contributor naming doc contains local filesystem links | Committed Markdown | Open | Replace with repository-relative links | Pending | Link validation required |
| `DRIFT-018` | ADRs lack a consolidated status index | Existing ADR files | Open | Architecture index | Pending | Ratification remains separate |

## Update Rule

Every Build Unit that changes a listed condition must update this ledger with the changed paths, commit SHA when known, and remaining risk. A documentation change does not resolve runtime or contract drift unless the relevant implementation and validation have also changed under a separately approved Initiative.
