# Add `docs/form990-ingest-plan.md`

## Summary

Create `docs/form990-ingest-plan.md` and place the Form 990 IRS ZIP/CSV design note there as the canonical planning document for the upcoming refactor. This step is documentation-only and should not change application code, infrastructure, tests, or runtime behavior.

## Implementation Changes

- Add a new markdown file at `docs/form990-ingest-plan.md`.
- Use the design note already drafted in this session as the full file contents.
- Preserve the current structure in the document:
  1. current Form 990 ingest flow as implemented
  2. exact gaps preventing correct IRS ZIP/CSV-driven processing
  3. proposed target flow
  4. files/modules to change
  5. backward-compatibility risks
  6. test plan
- Keep the document grounded in the repo’s current implementation:
  - current Lambda entrypoints and worker flow
  - current discovery, manifest, and ZIP-processing behavior
  - current execution modes and environment/Terraform naming
- Keep the business rules explicit in the document:
  - CSV index is authoritative for incremental selection
  - ZIP archives are authoritative for raw XML extraction
  - original IRS ZIP/CSV artifacts must be stored in S3
  - raw-source history must be preserved by key/manifests, not S3 versioning
- Include the observed filename patterns from `Form990Links.txt` as supported examples the future implementation must account for.

## Public Interfaces

- No public API, schema, or Terraform interface changes in this step.
- `README.md` remains unchanged until implementation changes behavior.

## Test Plan

- No test edits are required for the documentation-only addition.
- Validate only that the new markdown file is present in `docs/` and contains the finalized plan content.
- Defer all runtime and regression testing to the later implementation phase described in the document.

## Assumptions

- The content to write is exactly the design note already produced, without expanding scope beyond Form 990 ingest planning.
- The new doc is additive and does not replace any existing docs unless a later cleanup task explicitly does that.
