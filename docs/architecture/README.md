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
Last reconciled: 2026-09-04  
Canonical owner of: Navigation and status of technical-structure documentation  
Related Initiatives: `INIT-001`, `INIT-003`, `INIT-004`, `INIT-005`, `INIT-006`, `INIT-007`, `INIT-009`

Architecture organizes technical structure. It does not own the Mission, Strategic Outcomes, Initiative identity, or Roadmap priority.

## Architecture Sources

| Path | Purpose | Authority / status | Related Initiatives | Known conflicts / ratification needs |
|---|---|---|---|---|
| [`../../backend/README.md`](../../backend/README.md) | Current backend runtime-host boundaries, local development, persistence, and container contracts | Supporting current runtime reference | `INIT-003`, `INIT-004`, `INIT-005`, `INIT-007` | Verify implementation against current code, migrations, and tests |
| [`../../frontend/README.md`](../../frontend/README.md) | Frontend workspace and portal/shared dependency boundaries | Supporting current runtime reference | `INIT-005`, `INIT-008` | Product surfaces must not redefine authority |
| [`ADR-advisory-copilot-product-doctrine.md`](ADR-advisory-copilot-product-doctrine.md) | Customer-facing nonprofit advisory-copilot doctrine | Accepted decision | `INIT-001`, `INIT-005` | Legacy score/recommendation seams remain compatibility concerns |
| [`ADR-ecs-runtime-pivot.md`](ADR-ecs-runtime-pivot.md) | ECS/ALB customer API runtime direction | Architecture decision | `INIT-005`, `INIT-007` | Legacy rollback references require freshness checks |
| [`ADR-identity-datastore.md`](ADR-identity-datastore.md) | Identity datastore direction | Provisional ADR | `INIT-004` | Security/privacy/migration approval required for material changes |
| [`ADR-nonprofit-database-isolation.md`](ADR-nonprofit-database-isolation.md) | Nonprofit database isolation and persistence direction | Architecture decision | `INIT-002`, `INIT-003`, `INIT-007` | Verify current migration/runtime state before changing persistence |
| [`ADR-billing-provider.md`](ADR-billing-provider.md) | Billing provider direction | Provisional ADR | `INIT-006` | Production policy and operational decisions remain separate |
| [`evidence-review-contract.md`](evidence-review-contract.md) | Evidence-first nonprofit review contract | Architecture/product contract reference | `INIT-001`, `INIT-002`, `INIT-005` | Customer decision authority remains governing constraint |
| [`form990-local-workspace-architecture.md`](form990-local-workspace-architecture.md) | Local Form 990 workspace architecture | Supporting Architecture | `INIT-003` | Distinguish local workflow from deployed prerequisites |
| [`../monthly-ingest-architecture.md`](../monthly-ingest-architecture.md) | Monthly ingest workflow and contracts | Supporting Architecture | `INIT-003`, `INIT-007` | Distinguish implementation from environment prerequisites |
| [`../monthly-ingest-runbook.md`](../monthly-ingest-runbook.md) | Deployment and operational procedures | Supporting runbook | `INIT-003` | Operational source, not strategy |
| [`plan-catalog.md`](plan-catalog.md) | Runtime/architecture reference for plan catalog projection | Supporting reference | `INIT-006` | Product/package meaning is owned by `docs/product/plan-catalog.md` after ratification |
| [`portal-routing.md`](portal-routing.md) | Portal routing reference | Supporting reference | `INIT-005` | Verify against current portal route implementation |
| [`../../split-plan.json`](../../split-plan.json) | Machine-readable historical/transitional split mapping | Supporting compatibility contract | `INIT-001`, `INIT-007` | Do not treat stale target paths as current physical topology without repo evidence |

## Removed or Historical Architecture Paths

The following paths were referenced by earlier governance/index records but are not present on current `main` as of 2026-09-04:

- `docs/repo-target-architecture.md`
- `docs/repo-split-guide.md`
- `docs/backend-stage1-readiness.md`
- `docs/private-platform-service-areas.md`
- `docs/capability-naming-abstraction.md`
- `docs/contributor-naming-rules.md`
- `docs/infrastructure-naming-normalization.md`

Do not recreate these paths merely to satisfy historical references. Use current repository reality and the active sources above. Historical references should be treated as migration evidence until a separately approved documentation migration establishes replacement paths.

## Current Structural Model

Current repository reality uses first-class `frontend/`, `backend/`, and `infrastructure/` runtime/deployment boundaries, with `public-core/` and `private-platform/` retained as compatibility/evolution boundaries where still present. The current backend runtime hosts are documented under `backend/customer-api/`, `backend/platform-api/`, `backend/worker/`, `backend/ingest/federal/`, and `backend/shared/`.

Do not infer physical topology from older target-state documents when current paths, code, or tests disagree.

## Customer-Policy Ownership Boundary — Unresolved

`INIT-001` must resolve material customer-policy ownership changes before code movement or contract redesign.

### Reusable/open-safe candidates

- source-fact and evidence models
- normalization
- pure policy rule schemas
- pure deterministic rule evaluation
- generic scoring primitives with explicit semantics where retained internally

### Customer-private concerns

- customer policy definitions and assignment
- policy precedence, versions, and lifecycle
- customer-specific thresholds and required evidence
- policy authorization
- evaluation history and final customer decisions
- proprietary templates where applicable

The accepted advisory-copilot doctrine and customer decision-authority rules prohibit treating legacy score/recommendation seams as customer-facing product truth. This index records the unresolved implementation-placement distinction but does not ratify a source move, alter split-plan compatibility, or change runtime behavior.

## ADR Needed

A focused `INIT-001` Recon should produce an ADR proposal if evaluator versus customer-policy ownership, persistence/versioning, authorization, API compatibility, evidence snapshots, audit history, migration, or rollback requires a material architecture change.

## Reading Rule

Use the most specific current Architecture source for technical structure, then verify implementation against merged code, tests, schemas, and migrations. Record conflicts in the drift ledger. Do not promote a provisional ADR or historical target-state document to implemented fact without repository evidence.
