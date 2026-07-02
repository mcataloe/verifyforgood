<!--
LEAP_DOC_METADATA:
  audience: maintainer, agent, contributor
  doc_type: architecture-index
  authority: supporting
  applies_to: verifyforgood
END_LEAP_DOC_METADATA
-->

# VerifyForGood Architecture Index

Status: Active supporting index; individual decisions retain their own authority  
Owner / approver: Project owner / Architecture owner  
Last reconciled: 2026-07-02  
Canonical owner of: Navigation and status of technical-structure documentation  
Related Initiatives: `INIT-001`, `INIT-003`, `INIT-004`, `INIT-006`, `INIT-007`, `INIT-009`

Architecture organizes technical structure. It does not own the Mission, Strategic Outcomes, Initiative identity, or Roadmap priority.

## Architecture Sources

| Path | Purpose | Authority / status | Related Initiatives | Known conflicts / ratification needs |
|---|---|---|---|---|
| [`../repo-target-architecture.md`](../repo-target-architecture.md) | Current assessment and target repository split | Supporting / provisional | `INIT-001`, `INIT-007` | Broad policy/decision public-core classification needs refinement |
| [`../repo-split-guide.md`](../repo-split-guide.md) | Migration placement and dependency guidance | Supporting | `INIT-007` | Must remain compatible with current runtime paths |
| [`../backend-stage1-readiness.md`](../backend-stage1-readiness.md) | Entrypoint ownership and shared-contract readiness | Supporting snapshot | `INIT-005`, `INIT-007` | Preserve tested headings and paths |
| [`../monthly-ingest-architecture.md`](../monthly-ingest-architecture.md) | Monthly ingest workflow and contracts | Supporting Architecture | `INIT-003`, `INIT-007` | Distinguish implementation from environment prerequisites |
| [`../monthly-ingest-runbook.md`](../monthly-ingest-runbook.md) | Deployment and operational procedures | Supporting runbook | `INIT-003` | Operational source, not strategy |
| [`../private-platform-service-areas.md`](../private-platform-service-areas.md) | Private-platform service boundaries | Supporting / transitional | `INIT-004`, `INIT-006`, `INIT-007` | Service areas are persistent boundaries, not Initiatives |
| [`../capability-naming-abstraction.md`](../capability-naming-abstraction.md) | Neutral capability namespace and compatibility | Supporting convention | `INIT-007` | Preserve compatibility terms |
| [`../contributor-naming-rules.md`](../contributor-naming-rules.md) | Contributor naming rules | Supporting convention | `INIT-007`, `INIT-009` | Local filesystem links require repair |
| [`../infrastructure-naming-normalization.md`](../infrastructure-naming-normalization.md) | Terraform and physical-resource naming | Supporting convention | `INIT-007` | Deployed names require explicit migration |
| [`ADR-billing-provider.md`](ADR-billing-provider.md) | Billing provider direction | Provisional ADR | `INIT-006` | Production decisions remain separate |
| [`ADR-identity-datastore.md`](ADR-identity-datastore.md) | Identity datastore direction | Provisional ADR | `INIT-004` | Security/privacy/migration approval required |
| [`../../frontend/README.md`](../../frontend/README.md) | Frontend workspace boundaries | Supporting Architecture | `INIT-005`, `INIT-008` | Product surfaces must not redefine authority |
| [`../../split-plan.json`](../../split-plan.json) | Machine-readable split mapping | Supporting contract | `INIT-001`, `INIT-007` | Intentionally unchanged by `INIT-009`; policy distinction incomplete |

## Current Structural Model

The repository is transitioning toward:

- `public-core/` for reusable deterministic/open-safe logic
- `private-platform/` for customer/account/auth/billing/admin/runtime and proprietary concerns
- `infrastructure/` for deployment configuration and entrypoint wiring

Current runtime code still exists under legacy paths. Transitional documentation must not claim the physical split is complete.

## Customer-Policy Ownership Boundary — Unresolved

`INIT-001` must resolve this boundary before code movement.

### Reusable public-core candidates

- source-fact and evidence models
- normalization
- pure policy rule schemas
- pure deterministic rule evaluation
- generic scoring primitives with explicit semantics

### Customer-private private-platform concerns

- customer policy definitions and assignment
- policy precedence, versions, and lifecycle
- customer-specific thresholds and required evidence
- policy authorization
- evaluation history and final customer decisions
- proprietary templates where applicable

The existing target architecture and `split-plan.json` broadly list policy and decision modules as public-core candidates. This index records the unresolved distinction but does not ratify a source move, alter the split plan, or change runtime behavior.

## ADR Needed

A focused `INIT-001` Recon should produce an ADR proposal covering evaluator versus policy-definition ownership, persistence/versioning, authorization, API compatibility, evidence snapshots, audit history, migration, and rollback.

## Reading Rule

Use the most specific current Architecture source for technical structure, then verify implementation against merged code and tests. Record conflicts in the drift ledger. Do not promote a provisional ADR or target-state document to implemented fact without repository evidence.
