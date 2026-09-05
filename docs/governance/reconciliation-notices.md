<!--
LEAP_DOC_METADATA:
  audience: maintainer, agent, contributor
  doc_type: reconciliation-status
  authority: supporting
  applies_to: verifyforgood
END_LEAP_DOC_METADATA
-->

# Existing-Document Reconciliation Status

Status: Connector-safe reconciliation complete; bounded root-file patches still required  
Owner / approver: Project owner  
Last reconciled: 2026-09-04  
Related Initiative: `INIT-009`  
Related Build Unit: `BU-GOV-007`

## Completed Safely

Earlier governance work added non-destructive source-truth, Charter, strategy, Domain, Architecture, Delivery, Build, inventory, gap, drift, stale-source, and migration records.

The 2026-09-04 `BU-GOV-007` reconciliation pass rechecked current `main` rather than blindly applying the older pending list. It completed these bounded changes:

| Path | Change | Runtime impact |
|---|---|---|
| `CUSTOMER_README copy.md` | Added a visible do-not-use warning and pointers to current customer/source-truth documentation | None |
| `docs/implementation/portal-identity-membership-status.md` | Replaced unrelated customer-support wording and stale DynamoDB/GSI deployment notes with a bounded PostgreSQL/organization-context status snapshot | None |
| `docs/implementation/billing-subscription-status.md` | Verified current wording is already bounded as `billing track active` with remaining hardening work; no additional file edit required | None |
| `docs/architecture/README.md` | Refreshed the active Architecture index against current repository paths; removed broken active links to historical paths that are absent on current `main` | None |
| `docs/governance/stale-document-register.md` | Updated stale/reconciled document statuses | None |
| `docs/governance/migration-map.md` | Recorded current path state and stopped treating removed historical files as pending edits | None |
| `docs/governance/drift-ledger.md` | Updated `BU-GOV-007`-affected drift findings and resolving evidence | None |
| `docs/governance/gap-register.md` | Updated `BU-GOV-007`-affected gaps and identified the remaining root-file patch blocker | None |

## Historical Pending Items Reconciled Against Current Main

Two paths in the older `BU-GOV-007` remediation list are no longer present on current `main`:

- `docs/contributor-naming-rules.md`
- `docs/repo-target-architecture.md`

Several additional historical target/split/naming paths referenced by the older Architecture index are also absent. The current Architecture index now lists active current sources and records the removed historical paths without recreating them. Recreating deleted historical documents solely to satisfy stale references is not authorized by `BU-GOV-007`.

## Remaining Root-File Patches

Three large root files still require small, bounded edits:

| Path | Required change | Why not applied through the current connector |
|---|---|---|
| `AGENTS.md` | Update canonical documentation entry point, source-truth ordering, stale backend topology/commands, and references to removed architecture/naming paths | Repository guidance explicitly requires safe local/in-place patching rather than reconstructing this large instruction file through connector-only full-file replacement |
| `README.md` | Add the documentation-authority notice near the top and avoid treating stale mixed architecture details as project truth | The file is large and mixed-purpose; the recorded remediation requires safe bounded patching rather than whole-file reconstruction |
| `TODO.md` | Add a concise notice that TODO is backlog, not Strategy/Roadmap/source truth | The file is large; this is an in-place header edit and should not require whole-file reconstruction |

### Exact `AGENTS.md` Source-Truth Corrections

At minimum, the repository section must:

1. change the baseline entry point from root `README.md` to `docs/00_start_here.md`
2. identify `docs/charter/source-of-truth.md` and `docs/charter/decision-authority.md` as governing documentation sources
3. treat root `README.md` as a supporting compatibility/repository overview
4. align the project source-of-truth order with `docs/charter/source-of-truth.md`
5. replace stale runtime layout references such as `backend/api/` and `backend/ingest-task/` with the current `backend/customer-api/`, `backend/platform-api/`, `backend/worker/`, `backend/ingest/federal/`, and `backend/shared/` layout where those passages describe current topology
6. stop presenting removed historical paths such as `docs/repo-target-architecture.md` and `docs/contributor-naming-rules.md` as current primary sources
7. update local backend command examples from the stale `charity_status_backend...` namespace to the current `verification.backend...` namespace where current `backend/README.md` establishes the replacement

These are factual reconciliation changes, not new Architecture decisions.

### Exact `README.md` Authority Notice

Add near the top:

```text
## Documentation Authority

Start with `docs/00_start_here.md` for current project documentation navigation. This root README is a supporting repository overview and compatibility entry point, not the owner of all project truth.

For source-truth precedence, see `docs/charter/source-of-truth.md`. For customer decision-authority rules, see `docs/charter/decision-authority.md`. For product/package plan meaning, see `docs/product/plan-catalog.md` and exact structured values in `docs/product/plan-catalog.yaml`.

For questions about what the software currently does, inspect current merged code, tests, schemas, routes, infrastructure configuration, and public contracts. Documentation must distinguish implemented behavior from proposed or draft intent.
```

A later bounded README cleanup may reconcile stale architecture details such as older serving-cache statements, but `BU-GOV-007` must not silently redesign runtime architecture under a documentation edit.

### Exact `TODO.md` Ownership Notice

Add near the top:

```text
> `TODO.md` is an implementation/backlog list. It is not the canonical Strategy, Initiative registry, Roadmap, Architecture, or source-of-truth entry point. Start with `docs/00_start_here.md` for current project documentation navigation.
```

## Gate

`BU-GOV-007` is **not complete** until the three root-file patches above are applied with safe in-place/local patch tooling and the resulting documentation links/claims are validated. All connector-safe reconciliation items identified in the recorded set are complete as of 2026-09-04.
