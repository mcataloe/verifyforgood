<!--
LEAP_DOC_METADATA:
  audience: maintainer, agent, contributor
  doc_type: validation-report
  authority: supporting
  applies_to: verifyforgood
END_LEAP_DOC_METADATA
-->

# VerifyForGood INIT-009 Validation Report

Status: Partial validation — local execution required  
Owner / approver: Project owner  
Last reconciled: 2026-07-02  
Related Initiative: `INIT-009`  
Related Build Unit: `BU-GOV-008`

## Repository Comparison

- Base: `main`
- Base commit: `694d07e1315ce266b274d6ca5008ca7a2e6a5f60`
- Branch: `docs/leap-documentation-baseline-v2`
- Branch state inspected before this report: `ee555675c688f7fe0a613290e24a6c6d6cb1fddf`
- Comparison status: branch ahead, not behind
- Changed-file scope: added Markdown files under `docs/` only
- Existing files modified: none
- Files deleted or moved: none
- Runtime, API, schema, data, auth, billing, infrastructure, frontend, policy, and test source changes: none

## Required Paths

Verified through the repository comparison:

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

- Strategic Outcome IDs `SO-001` through `SO-008` are unique.
- Initiative IDs `INIT-001` through `INIT-009` are unique.
- Every Initiative in the registry references one or more Strategic Outcomes.
- `INIT-009` records `DU-GOV-001` and `DU-GOV-002`.
- `BU-GOV-001` through `BU-GOV-008` reference `INIT-009` and a Delivery Unit.
- Domains used by the Initiative registry are represented in the Domain map at the documented level of detail.
- Roadmap placement remains separate from Initiative identity.
- Historical Phase labels remain present in the migration and Build Unit records.

## Manual Link Review

The canonical links from `docs/00_start_here.md` point to files present on the branch. The Architecture index points to existing repository paths inspected during Recon. A full Markdown link crawler was not available in this connector-only environment.

Known pre-existing broken local links in `docs/contributor-naming-rules.md` remain unresolved and are recorded in `reconciliation-notices.md`.

## Trust-Language Review

The new documentation consistently distinguishes:

- source facts
- normalized facts
- evidence state
- platform-derived signals
- baseline compatibility evaluations
- customer policy results
- customer determinations

The new documents do not claim that VerifyForGood universally determines nonprofit eligibility, approval, denial, legal compliance, tax treatment, sanctions disposition, fraud status, grant/procurement suitability, or donation suitability.

Existing product and customer documents still require the bounded reconciliation listed in `reconciliation-notices.md`.

## Checks Not Run

The following checks require a local checkout or CI execution and were not available through the connected GitHub file operations:

```text
git status --short
git diff --check
Markdown relative-link validation
local-path scan with ripgrep
targeted pytest suite
full pytest suite
```

No claim of passing local or full test validation is made.

## Build Unit Status

- `BU-GOV-001` through `BU-GOV-006`: Completed on the branch.
- `BU-GOV-007`: Incomplete; safe updates to existing files were blocked by connector controls.
- `BU-GOV-008`: Partially completed; remote structure/scope/traceability review passed, local tests and link checks remain required.
- `DU-GOV-001`: Complete subject to project-owner ratification of Draft documents.
- `DU-GOV-002`: Incomplete.
- `INIT-009`: Active, not complete.

## Required Local Validation

Before merge:

```bash
git fetch --all --prune
git switch docs/leap-documentation-baseline-v2
git status --short
git diff --check origin/main...HEAD
rg -n '([A-Za-z]:\\|/Users/|/home/[^/]+/|file://)' --glob '*.md'
python -m pytest -q tests/test_repo_split_scaffolding.py tests/test_backend_stage1_readiness.py tests/test_infrastructure_naming.py tests/test_platform_branding.py
python -m pytest -q
```

Also run a repository-relative Markdown link check and apply the existing-file updates in `reconciliation-notices.md` without changing runtime or public contracts.

## Gate

`CONDITIONAL PROCEED`

The new source-truth baseline is ready for project-owner review. Merge is not recommended until `BU-GOV-007` is completed and local `BU-GOV-008` validation passes.
