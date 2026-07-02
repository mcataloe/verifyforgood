<!--
LEAP_DOC_METADATA:
  audience: maintainer, agent, contributor
  doc_type: build-unit-index
  authority: canonical
  applies_to: verifyforgood
END_LEAP_DOC_METADATA
-->

# VerifyForGood Build Units

A Build Unit is a bounded implementation responsibility that can be implemented, tested, reviewed, and usually committed independently. It is not required to be independently deployable.

## Required Metadata

- Build Unit ID
- Initiative and Delivery Unit
- Objective
- Scope and out of scope
- Affected Domains and Architecture areas
- Dependencies and sequencing constraints
- Files and areas to inspect
- Files and areas not to touch
- Acceptance criteria
- Validation evidence
- Stop conditions
- Commit guidance
- Status and last reconciliation

## Active Records

- [`INIT-009 — Documentation and Traceability Baseline`](INIT-009.md)

Build Units must remain within approved scope and stop when a material product, Architecture, contract, or source-truth decision is required.
