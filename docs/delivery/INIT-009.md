<!--
LEAP_DOC_METADATA:
  audience: maintainer, agent, contributor
  doc_type: delivery-unit-record
  authority: canonical
  applies_to: verifyforgood
END_LEAP_DOC_METADATA
-->

# INIT-009 — LEAP Documentation and Traceability Baseline

Status: Active  
Owner / approver: Project owner  
Last reconciled: 2026-07-02  
Strategic Outcomes: `SO-002`, `SO-004`, `SO-007`, `SO-008`

## Initiative Purpose

Establish a discoverable, internally consistent Mission-to-Build-Unit documentation baseline and reconcile existing documentation without changing runtime behavior, APIs, schemas, data, authentication, billing, infrastructure, or policy behavior.

## DU-GOV-001 — Discoverable Project Source-Truth Baseline

- **Status:** Completed on the documentation branch; Draft strategy still requires owner ratification.
- **Outcome:** Contributors and agents can locate Mission, customer decision authority, source-truth rules, Outcomes, Initiatives, Roadmap, Domains, Architecture, Delivery Units, Build Units, and governance records.
- **Adoption boundary:** A contributor starting at `docs/00_start_here.md` can navigate the hierarchy and distinguish evidence, platform signals, policy results, and customer determinations.
- **Scope:** `BU-GOV-001` through `BU-GOV-006`.
- **Non-goals:** Runtime/contract change, ratification by inference, deletion, or relocation.
- **Dependencies:** Approved Recon, customer decision-authority principle, repository evidence, LEAP documentation model.
- **Acceptance:** Required source-truth files exist and cross-link; statuses are explicit; existing paths remain intact.
- **Validation:** `BU-GOV-008`.
- **Rollback:** Revert bounded documentation commits.

## DU-GOV-002 — Existing Documentation Reconciliation

- **Status:** Active with documented connector limitations.
- **Outcome:** Existing high-value documents identify their authority and canonical owners; stale/conflicting sources are visible; safe links are repaired; validation is reported honestly.
- **Scope:** `BU-GOV-007` and `BU-GOV-008`.
- **Non-goals:** Comprehensive rewrite, deletion, physical migration, API or runtime changes.
- **Dependencies:** `DU-GOV-001` and safe update access to existing files.
- **Acceptance:** Existing paths remain; warnings and links are clear; no prohibited files change; unresolved updates remain in the gap/drift records.
- **Validation:** `BU-GOV-008`.
- **Rollback:** Revert reconciliation/validation commits independently.

## Build Units

- `BU-GOV-001 — Inventory Current Documentation`
- `BU-GOV-002 — Establish Source-of-Truth Manifest`
- `BU-GOV-003 — Draft Project Charter and Decision Authority`
- `BU-GOV-004 — Establish Strategy and Initiative Registry`
- `BU-GOV-005 — Establish Domain and Architecture Indexes`
- `BU-GOV-006 — Establish Delivery and Build Traceability`
- `BU-GOV-007 — Reconcile Existing Documents`
- `BU-GOV-008 — Validate and Hand Off Documentation Baseline`

## Risks

- accidental ratification of Draft strategy
- broken tested paths or headings
- loss of historical Phase traceability
- unsupported verification/compliance language
- source-truth duplication
- local-only work not visible to remote execution
- connector safety restrictions preventing some existing-file updates
