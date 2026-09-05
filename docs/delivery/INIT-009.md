<!--
LEAP_DOC_METADATA:
  audience: maintainer, agent, contributor
  doc_type: delivery-unit-record
  authority: canonical
  applies_to: verifyforgood
END_LEAP_DOC_METADATA
-->

# INIT-009 — LEAP Documentation and Traceability Baseline

Status: Baseline implementation complete; Draft/Proposed governance and strategy documents retain their stated ratification status  
Owner / approver: Project owner  
Last reconciled: 2026-09-04  
Strategic Outcomes: `SO-002`, `SO-004`, `SO-007`, `SO-008`

## Initiative Purpose

Establish a discoverable, internally consistent Mission-to-Build-Unit documentation baseline and reconcile existing documentation without changing runtime behavior, APIs, schemas, data, authentication, billing, infrastructure, or policy behavior.

## DU-GOV-001 — Discoverable Project Source-Truth Baseline

- **Status:** Completed; Draft strategy/Charter content still requires owner ratification where explicitly marked.
- **Outcome:** Contributors and agents can locate Mission, customer decision authority, source-truth rules, Outcomes, Initiatives, Roadmap, Domains, Architecture, Delivery Units, Build Units, and governance records.
- **Adoption boundary:** A contributor starting at `docs/00_start_here.md` can navigate the hierarchy and distinguish evidence, platform signals, policy results, and customer determinations.
- **Scope:** `BU-GOV-001` through `BU-GOV-006`.
- **Non-goals:** Runtime/contract change, ratification by inference, deletion, or relocation.
- **Dependencies:** Approved Recon, customer decision-authority principle, repository evidence, LEAP documentation model.
- **Acceptance:** Required source-truth files exist and cross-link; statuses are explicit; existing paths remain intact or removed historical paths are recorded without recreation.
- **Validation:** `BU-GOV-008` completed with recorded connector/runtime-test execution limitation.
- **Rollback:** Revert bounded documentation commits.

## DU-GOV-002 — Existing Documentation Reconciliation

- **Status:** Completed 2026-09-04.
- **Outcome:** Existing high-value documents identify their authority and canonical owners; stale/conflicting sources are visible; entry points/topology are reconciled; validation limitations are reported honestly.
- **Scope:** `BU-GOV-007` and `BU-GOV-008`.
- **Non-goals:** Comprehensive rewrite, deletion, physical migration, API or runtime changes.
- **Dependencies:** `DU-GOV-001` and safe repository update access.
- **Acceptance:** Root entry points are aligned; stale duplicate/status records are bounded; active Architecture links reflect current paths; no runtime/test source changed; unresolved product/contract questions remain in their proper Initiatives.
- **Validation:** `BU-GOV-008`.
- **Rollback:** Revert reconciliation/validation commits independently.

## Build Units

- `BU-GOV-001 — Inventory Current Documentation` — Completed
- `BU-GOV-002 — Establish Source-of-Truth Manifest` — Completed
- `BU-GOV-003 — Draft Project Charter and Decision Authority` — Completed; Draft/approved-principle statuses preserved
- `BU-GOV-004 — Establish Strategy and Initiative Registry` — Completed; Draft statuses preserved
- `BU-GOV-005 — Establish Domain and Architecture Indexes` — Completed
- `BU-GOV-006 — Establish Delivery and Build Traceability` — Completed
- `BU-GOV-007 — Reconcile Existing Documents` — Completed
- `BU-GOV-008 — Validate and Hand Off Documentation Baseline` — Completed with explicit validation limitation

## Validation Limitation

The final baseline validation used current repository evidence through the GitHub connector. No local checkout was mounted, so Python tests and local git/Markdown tooling were not executed. The earlier targeted pytest recipe was itself stale because the four named tests no longer exist on current `main`. This documentation-only Initiative did not change runtime or test source.

This limitation does not waive validation for future implementation work: every subsequent feature/Build Unit must run its own current repository preflight and relevant local/CI checks.

## Risks Carried Forward Outside INIT-009

- Draft Charter/strategy/product documents are not ratified by completion of this documentation Initiative.
- legacy score/eligibility/approve/deny semantics remain governed by `INIT-001` gaps and decisions.
- product plan-catalog ratification/runtime projection remains separate.
- historical Phase classification remains incomplete where explicitly recorded.
- the root README still contains mixed historical/current implementation material, but its authority is now explicitly bounded.
