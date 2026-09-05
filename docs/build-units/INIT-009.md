<!--
LEAP_DOC_METADATA:
  audience: maintainer, agent, contributor
  doc_type: build-unit-registry
  authority: canonical
  applies_to: verifyforgood
END_LEAP_DOC_METADATA
-->

# INIT-009 Build Units

Status: Baseline implementation complete; Draft/Proposed documents retain their stated ratification status  
Owner / approver: Project owner  
Last reconciled: 2026-09-04  
Initiative: `INIT-009 — LEAP Documentation and Traceability Baseline`

## Common Constraints

- Documentation-only.
- Preserve existing paths and historical Phase identifiers.
- Do not change runtime, API, schema, data, authentication, billing, infrastructure, pricing, or policy behavior.
- Do not modify `split-plan.json` or test source files.
- New strategic documents remain Draft unless explicitly marked as an approved principle.

| Build Unit | Delivery Unit | Objective | Status | Commit guidance |
|---|---|---|---|---|
| `BU-GOV-001` | `DU-GOV-001` | Inventory documents, gaps, and drift before generating source truth | Completed | `docs(governance): inventory and classify current documentation` |
| `BU-GOV-002` | `DU-GOV-001` | Establish navigation, source precedence, stale register, and migration map | Completed | `docs(governance): establish project source-truth manifest` |
| `BU-GOV-003` | `DU-GOV-001` | Draft Charter and record approved customer decision authority | Completed; Charter Draft | `docs(charter): define customer-owned decision authority` |
| `BU-GOV-004` | `DU-GOV-001` | Establish Outcomes, Initiative registry, and Roadmap | Completed; strategy Draft | `docs(strategy): add outcomes, initiatives, and roadmap` |
| `BU-GOV-005` | `DU-GOV-001` | Establish Domain map and Architecture index | Completed | `docs(architecture): add domain and architecture indexes` |
| `BU-GOV-006` | `DU-GOV-001` | Establish Delivery and Build traceability and Phase classification | Completed | `docs(delivery): establish delivery and build traceability` |
| `BU-GOV-007` | `DU-GOV-002` | Reconcile existing entry points, stale sources, links, and status records | Completed 2026-09-04 | `docs(reconciliation): align existing docs with LEAP source truth` |
| `BU-GOV-008` | `DU-GOV-002` | Validate required paths, links, IDs, trust language, tests, and changed-file scope | Completed with recorded connector/runtime-test execution limitation | `docs(validation): complete LEAP documentation baseline` |

## BU-GOV-008 Validation Boundary

`BU-GOV-008` validates the documentation baseline itself. Current-repository path/source-truth/traceability/trust-language and changed-scope checks were completed from repository evidence.

A Python runtime test suite was not executed in the connector-only environment because no local checkout is mounted. The historical targeted pytest command recorded by the earlier validation report had also drifted: the four named test files no longer exist on current `main`. No runtime or test source changed under `BU-GOV-007` or `BU-GOV-008`, so this limitation is recorded rather than treating obsolete test paths as a blocker to the documentation-only Build Unit.

Future implementation work must still perform its own current local/CI preflight and relevant tests.

## Historical Phase Classification

| Legacy artifact | Classification | Initiative mapping | Status |
|---|---|---|---|
| Phase 6B policy engine | Historical Delivery Unit or Build Unit | `INIT-001` | Needs detailed reconciliation |
| Phase 8B weighting profiles | Historical Build Unit | `INIT-001`, `INIT-002` | Provisional |
| Phase 10 Form 990 work | Delivery and Build Units | `INIT-003` | Needs detailed reconciliation |
| Phase 12 billing model | Historical Delivery Unit | `INIT-006` | Provisional |
| Phase 15 frontend/docs work | Delivery Units | `INIT-005` and/or `INIT-008` | Needs reconciliation |
| Phase 20 tenant-aware API work | Delivery Units | `INIT-004`, `INIT-005` | Provisional |
| Phase 21 billing work | Delivery Units | `INIT-006` | Provisional |
| Phase 22 customer administration | Delivery Units | `INIT-004`, `INIT-005` | Provisional |
| `PLAN.md` Phase 1–3 | Completed Build Units | `INIT-003` | Historical |
| Step Functions phases | Operational process stages | `INIT-003` | Preserve |
| Architecture migration stages | Chronological Architecture phases | `INIT-007` | Preserve |
| Qualified `PlatformLayer` values | Architecture Layers | Architecture view | Preserve |

## Validation and Stop Rule

Each Build Unit must report its evidence and limitations. When a material product, Architecture, contract, or source-truth decision is needed, record the issue and stop rather than infer a resolution.
