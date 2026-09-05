<!--
LEAP_DOC_METADATA:
  audience: maintainer, agent, contributor
  doc_type: validation-report
  authority: supporting
  applies_to: verifyforgood
END_LEAP_DOC_METADATA
-->

# VerifyForGood INIT-009 Validation Report

Status: Partial validation — root-file patching and local/CI execution still required  
Owner / approver: Project owner  
Last reconciled: 2026-09-04  
Related Initiative: `INIT-009`  
Related Build Unit: `BU-GOV-008`

## Current Repository State Reviewed

This validation refresh reviewed current `main` after the connector-safe `BU-GOV-007` reconciliation work.

Completed connector-safe reconciliation includes:

- visible `Do Not Use` warning on `CUSTOMER_README copy.md`
- corrected portal identity/membership status wording and PostgreSQL/organization-context baseline
- confirmation that billing status is already bounded as `billing track active`
- Architecture index reconciliation against paths that exist on current `main`
- governance updates for stale-document status, migration status, drift, gaps, reconciliation status, and `INIT-009` Build Unit status

No runtime, API, schema, authentication, billing, infrastructure, pricing, or policy behavior was intentionally changed by this reconciliation work.

## Required Paths

Current repository inspection confirms the core LEAP documentation baseline remains present:

- `docs/00_start_here.md`
- `docs/charter/project-charter.md`
- `docs/charter/source-of-truth.md`
- `docs/charter/decision-authority.md`
- `docs/strategy/strategic-outcomes.md`
- `docs/strategy/initiative-registry.md`
- `docs/strategy/roadmap.md`
- `docs/domains/domain-map.md`
- `docs/architecture/README.md`
- `docs/delivery/README.md`
- `docs/delivery/INIT-009.md`
- `docs/build-units/README.md`
- `docs/build-units/INIT-009.md`
- `docs/governance/documentation-inventory.md`
- `docs/governance/gap-register.md`
- `docs/governance/migration-map.md`
- `docs/governance/drift-ledger.md`
- `docs/governance/stale-document-register.md`
- `docs/governance/reconciliation-notices.md`

## Traceability Review

The established traceability model remains intact:

- Strategic Outcomes are represented under `docs/strategy/`.
- Initiatives are represented in the Initiative registry.
- `INIT-009` owns `DU-GOV-001` and `DU-GOV-002`.
- `BU-GOV-001` through `BU-GOV-008` remain registered under `INIT-009`.
- Roadmap, Domains, Architecture, Delivery Units, and Build Units remain separate planning/structure views.
- Historical Phase labels remain preserved rather than mechanically renamed.

## Remote Drift Checks

Remote repository search still finds the known root-file drift in `AGENTS.md`:

- `Current source-truth entry point | README.md`
- legacy `backend/api/` and `backend/ingest-task/` path references
- legacy `charity_status_backend.api.entrypoint` and `charity_status_backend.shared.local_dev` command references

These findings confirm that `BU-GOV-007` is not complete until the recorded bounded `AGENTS.md` patch is applied.

The root `README.md` still requires the recorded documentation-authority notice, and `TODO.md` still requires the recorded backlog/source-truth notice.

## Link / Removed-Path Review

Current repository reality no longer contains:

- `docs/repo-target-architecture.md`
- `docs/contributor-naming-rules.md`

The governance records have been reconciled so `BU-GOV-007` does not require recreating those removed legacy files merely to satisfy an outdated remediation note.

The Architecture index now documents current existing sources instead of relying on those removed paths.

## Trust-Language Review

Current governing documentation continues to distinguish evidence and derived signals from customer determinations. The accepted advisory-copilot doctrine requires customer-facing nonprofit experiences to avoid final recommendations, endorsements, ranking language, and platform-owned product-truth scores.

The stale duplicate customer guide is now visibly marked `Do Not Use`, reducing the risk that its stronger legacy claims are mistaken for current product truth.

## Checks Performed Remotely

- required-path presence review
- Initiative / Delivery Unit / Build Unit traceability review
- Architecture-index path reconciliation
- stale source-status review
- targeted search for known legacy backend path/command references
- targeted search for the stale README-first source-truth entry point
- latest GitHub commit status check for the reconciliation commit; no status checks were reported by GitHub

## Checks Not Run

A true local checkout or CI runner is still required for:

```text
git status --short
git diff --check
Markdown relative-link validation
local-path scan with ripgrep
targeted pytest suite
full pytest suite
```

The required local validation sequence remains:

```bash
git fetch --all --prune
git status --short
git diff --check
rg -n '([A-Za-z]:\\|/Users/|/home/[^/]+/|file://)' --glob '*.md'
python -m pytest -q tests/test_repo_split_scaffolding.py tests/test_backend_stage1_readiness.py tests/test_infrastructure_naming.py tests/test_platform_branding.py
python -m pytest -q
```

Also run a repository-relative Markdown link checker.

## Build Unit Status

- `BU-GOV-001` through `BU-GOV-006`: Completed.
- `BU-GOV-007`: In progress; connector-safe reconciliation is complete, but bounded edits to `AGENTS.md`, root `README.md`, and `TODO.md` remain required.
- `BU-GOV-008`: Remote validation refreshed and passed for discoverable structure/traceability checks; local/CI validation remains required.
- `DU-GOV-001`: Complete subject to the documented ratification posture of Draft documents.
- `DU-GOV-002`: Incomplete until `BU-GOV-007` root-file patches and local/CI `BU-GOV-008` checks complete.
- `INIT-009`: Active, not complete.

## Gate

`BLOCKED ON LOCAL PATCH + VALIDATION`

Do not close `BU-GOV-007`, `BU-GOV-008`, `DU-GOV-002`, or `INIT-009` until the three recorded root-file edits are applied with true in-place patching and the local/CI validation sequence passes.
