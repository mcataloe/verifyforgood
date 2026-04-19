# Capability Naming Abstraction

## Purpose

The platform now supports a neutral internal namespace, `verification_platform`, alongside the legacy `verification` package paths.

This phase does not rename infrastructure resources, environment variables, or existing package roots. It introduces a capability-oriented naming layer so new internal code can describe what the system does without embedding product or repository branding in the module path.

For the concise contributor rule set across runtime and infrastructure, see `docs/contributor-naming-rules.md`.

## Why This Exists

Current naming already separates customer-facing brand configuration from many runtime concerns, but package imports still lean heavily on the legacy `verification` root inherited from the existing codebase and repository history.

The abstraction layer solves that incrementally:

- new capability-oriented imports can use `verification_platform.*`
- existing `verification.*` imports remain valid and unchanged
- runtime behavior stays identical because the neutral namespace is implemented as re-exports over the current modules

## Naming Rule Going Forward

New internal module names should describe capability and responsibility, not brand or repository identity.

Three naming layers now apply:

- product / brand naming:
  - customer-facing labels such as `VerifyForGood`
- capability / domain naming:
  - preferred internal names such as `verification_platform` and `organization_verification`
- legacy compatibility naming:
  - preserved roots such as `verification`, `charitystatusapi`, and `CharityStatusAPI`

Preferred pattern:

- `verification_platform.organization_verification`
- `verification_platform.nonprofit_registry`
- `verification_platform.filing_ingestion`
- `verification_platform.compliance_data`
- `verification_platform.entity_resolution`
- `verification_platform.source_connectors`
- `verification_platform.platform_contracts`

Avoid new module names that bake in:

- current product brand names
- repository names
- customer-facing marketing terms
- source-specific branding when a capability name is sufficient

Keep public API contract terms unchanged unless a separate contract change is intentional. For example, existing `/v1/nonprofit/...` routes can remain even while internal modules move toward capability-oriented naming.

## Neutral Namespace Mapping

The initial wrapper layer maps to the existing modules like this:

- `verification_platform.organization_verification`
  - `verification.query`
  - `verification.decision`
  - `verification.evidence`
  - `verification.policy`
  - `verification.scoring`
- `verification_platform.nonprofit_registry`
  - `verification.state_registry`
- `verification_platform.filing_ingestion`
  - `verification.form990`
  - `verification.ingest`
- `verification_platform.compliance_data`
  - `verification.enrichments`
  - `verification.enrichments.compliance`
  - `verification.enrichments.external_signals`
- `verification_platform.entity_resolution`
  - `verification.normalization`
- `verification_platform.source_connectors`
  - `verification.sources`
  - `verification.ingest`
- `verification_platform.platform_contracts`
  - `verification.core`
  - `verification.platform`

This mapping is also captured in `verification_platform.legacy`.

## Legacy To Neutral Domain Map

The first core-domain rename layer maps these legacy concepts to capability-oriented names:

| Legacy term | Neutral term |
| --- | --- |
| charity lookup | organization verification |
| charity record | organization record |
| charity filings | regulatory filings |
| state compliance extraction | jurisdiction compliance interpretation |
| enrichment service | entity enrichment service |
| normalized source record | normalized organization source record |
| source catalog | source connector catalog |
| EIN normalization | employer identification number validation |

Concrete migrated module seams in this phase:

- `verification.query.nonprofit_lookup.map_nonprofit_record`
  - `verification_platform.organization_verification.organization_lookup.map_organization_record`
- `verification.query.verification.verify_nonprofit`
  - `verification_platform.organization_verification.verification_service.verify_organization`
- `verification.query.verification.get_nonprofit_filings`
  - `verification_platform.organization_verification.regulatory_filings.get_regulatory_filings`
- `verification.normalization.ein.normalize_ein`
  - `verification_platform.entity_resolution.ein_validation.normalize_employer_identification_number`
- `verification.enrichments.compliance.extract_state_compliance`
  - `verification_platform.compliance_data.interpretation.interpret_jurisdiction_compliance`
- `verification.enrichments.service.EnrichmentService`
  - `verification_platform.compliance_data.entity_enrichment.EntityEnrichmentService`
- `verification.sources.NormalizedSourceRecord`
  - `verification_platform.source_connectors.NormalizedOrganizationSourceRecord`
- `verification.sources.SourceCatalog`
  - `verification_platform.source_connectors.SourceConnectorCatalog`

## Compatibility Model

Backward compatibility is preserved by keeping legacy imports intact:

- existing code may continue importing from `verification.*`
- new code may import from `verification_platform.*`
- both paths resolve to the same underlying objects during this phase
- historical compatibility roots `charitystatusapi.*` and `CharityStatusAPI.*` now proxy to the supported runtime modules and emit deprecation warnings

That keeps rename risk low while giving later phases a neutral target namespace.

## Legacy Import Compatibility

Supported compatibility roots:

| Historical import root | Runtime target | Preferred destination for new code |
| --- | --- | --- |
| `charitystatusapi.*` | `verification.*` | `verification_platform.*` |
| `CharityStatusAPI.*` | `verification.*` | `verification_platform.*` |

Contributor guidance:

- do not add new implementation code under `charitystatusapi` or `CharityStatusAPI`
- keep those packages as thin shims only
- add any new capability-oriented naming under `verification_platform`
- keep `verification` working until a later deprecation/removal phase is explicitly planned

## Future-Proofing Benefits

This approach reduces future rename cost because:

- product-brand changes do not require immediate package renames
- capability boundaries become clearer before any code movement
- later migration phases can move implementations behind stable capability wrappers
- split-repo or package-extraction work can converge on neutral domains without breaking existing import paths first

## Later Rename Risks

The biggest risk areas for later rename phases are still:

- deep internal imports across `verification.*` modules
- path-sensitive packaging and extraction work in `public-core/` and `private-platform/`
- docs and generated artifacts that still mention the repository name explicitly
- duplicated scaffolding under `frontend/` that mirrors current package naming

Those later phases should be handled separately from this abstraction layer.

