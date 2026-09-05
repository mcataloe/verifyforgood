<!--
LEAP_DOC_METADATA:
  audience: maintainer, agent, contributor
  doc_type: reconciliation-status
  authority: supporting
  applies_to: verifyforgood
END_LEAP_DOC_METADATA
-->

# Existing-Document Reconciliation Status

Status: Complete for `BU-GOV-007`  
Owner / approver: Project owner  
Last reconciled: 2026-09-04  
Related Initiative: `INIT-009`  
Related Build Unit: `BU-GOV-007`

## Completed Reconciliation

The 2026-09-04 reconciliation rechecked current `main` against the recorded `BU-GOV-007` remediation set and applied the bounded documentation-only changes that remained relevant.

| Path | Reconciled change | Runtime impact |
|---|---|---|
| `AGENTS.md` | Canonical documentation entry point changed to `docs/00_start_here.md`; source-truth precedence aligned; current backend topology, namespaces, commands, migration paths, and documentation references refreshed | None |
| `README.md` | Added Documentation Authority notice identifying the README as a supporting compatibility/repository overview and linking canonical truth owners | None |
| `TODO.md` | Added explicit notice that TODO is implementation/backlog material rather than Strategy, Roadmap, Architecture, or source-truth entry point | None |
| `CUSTOMER_README copy.md` | Added visible do-not-use warning and pointers to current customer/source-truth documentation | None |
| `docs/implementation/portal-identity-membership-status.md` | Replaced unrelated customer-support wording and stale DynamoDB/GSI guidance with a bounded PostgreSQL/organization-context status snapshot | None |
| `docs/implementation/billing-subscription-status.md` | Verified current wording is already bounded as `billing track active`; no further edit required | None |
| `docs/architecture/README.md` | Refreshed the active Architecture index against current repository paths and removed broken active references to absent historical files | None |
| governance records | Refreshed stale-document, migration, drift, gap, reconciliation, Build Unit, Delivery Unit, and validation status to match current repository reality | None |

## Historical Pending Items Reconciled Against Current Main

Two files named in the older remediation set are no longer present on current `main`:

- `docs/contributor-naming-rules.md`
- `docs/repo-target-architecture.md`

They were not recreated. The Architecture index and migration records now preserve their historical significance without presenting them as active sources.

## Root-File Patch Verification

The root-file changes were applied through GitHub content updates after reconstructing each current file from repository reads. Commit-level diffs were inspected afterward:

- `AGENTS.md`: `890878ff59f1bd50a98b040d910c0f360c398a1f`
- `README.md`: `5d206f8ba20b807adef110b5c46a6172e9b4d704`
- `TODO.md`: `3c6d76802a12a9f9ffcf14e4cfd07b1ea7c51d22`

The README and TODO reconstructions produced a few incidental blank-line-only deletions. No substantive content was removed by those incidental formatting differences.

## Remaining Work Outside BU-GOV-007

`BU-GOV-007` does not resolve unrelated product/contract/Architecture questions already assigned elsewhere, including:

- legacy scoring and approve/deny semantics under `INIT-001`
- customer policy authoring/versioning and evaluator/private-policy ownership
- product plan-catalog ratification/runtime projection
- historical Phase classification that still needs evidence-based refinement
- stale implementation claims inside the large mixed root README that require their own bounded reconciliation if they become material

Those are explicitly separate from the existing-document reconciliation Build Unit.

## Gate

`BU-GOV-007` is **Completed**. The recorded entry-point, stale-source, link/path, and high-confidence status reconciliation set has been applied without runtime, API, schema, auth, billing, infrastructure, or policy behavior changes.
