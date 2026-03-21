# Capability Naming Abstraction

## Purpose

The platform now supports a neutral internal namespace, `verification_platform`, alongside the legacy `charity_status` package paths.

This phase does not rename infrastructure resources, environment variables, or existing package roots. It introduces a capability-oriented naming layer so new internal code can describe what the system does without embedding product or repository branding in the module path.

## Why This Exists

Current naming already separates customer-facing brand configuration from many runtime concerns, but package imports still lean heavily on the legacy `charity_status` root inherited from the existing codebase and repository history.

The abstraction layer solves that incrementally:

- new capability-oriented imports can use `verification_platform.*`
- existing `charity_status.*` imports remain valid and unchanged
- runtime behavior stays identical because the neutral namespace is implemented as re-exports over the current modules

## Naming Rule Going Forward

New internal module names should describe capability and responsibility, not brand or repository identity.

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

## Neutral Namespace Mapping

The initial wrapper layer maps to the existing modules like this:

- `verification_platform.organization_verification`
  - `charity_status.query`
  - `charity_status.decision`
  - `charity_status.evidence`
  - `charity_status.policy`
  - `charity_status.scoring`
- `verification_platform.nonprofit_registry`
  - `charity_status.state_registry`
- `verification_platform.filing_ingestion`
  - `charity_status.form990`
  - `charity_status.ingest`
- `verification_platform.compliance_data`
  - `charity_status.enrichments`
  - `charity_status.enrichments.compliance`
  - `charity_status.enrichments.external_signals`
- `verification_platform.entity_resolution`
  - `charity_status.normalization`
- `verification_platform.source_connectors`
  - `charity_status.sources`
  - `charity_status.ingest`
- `verification_platform.platform_contracts`
  - `charity_status.core`
  - `charity_status.platform`

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

- `charity_status.query.nonprofit_lookup.map_nonprofit_record`
  - `verification_platform.organization_verification.organization_lookup.map_organization_record`
- `charity_status.query.verification.verify_nonprofit`
  - `verification_platform.organization_verification.verification_service.verify_organization`
- `charity_status.query.verification.get_nonprofit_filings`
  - `verification_platform.organization_verification.regulatory_filings.get_regulatory_filings`
- `charity_status.normalization.ein.normalize_ein`
  - `verification_platform.entity_resolution.ein_validation.normalize_employer_identification_number`
- `charity_status.enrichments.compliance.extract_state_compliance`
  - `verification_platform.compliance_data.interpretation.interpret_jurisdiction_compliance`
- `charity_status.enrichments.service.EnrichmentService`
  - `verification_platform.compliance_data.entity_enrichment.EntityEnrichmentService`
- `charity_status.sources.NormalizedSourceRecord`
  - `verification_platform.source_connectors.NormalizedOrganizationSourceRecord`
- `charity_status.sources.SourceCatalog`
  - `verification_platform.source_connectors.SourceConnectorCatalog`

## Compatibility Model

Backward compatibility is preserved by keeping legacy imports intact:

- existing code may continue importing from `charity_status.*`
- new code may import from `verification_platform.*`
- both paths resolve to the same underlying objects during this phase
- historical compatibility roots `charitystatusapi.*` and `CharityStatusAPI.*` now proxy to the supported runtime modules and emit deprecation warnings

That keeps rename risk low while giving later phases a neutral target namespace.

## Legacy Import Compatibility

Supported compatibility roots:

| Historical import root | Runtime target | Preferred destination for new code |
| --- | --- | --- |
| `charitystatusapi.*` | `charity_status.*` | `verification_platform.*` |
| `CharityStatusAPI.*` | `charity_status.*` | `verification_platform.*` |

Contributor guidance:

- do not add new implementation code under `charitystatusapi` or `CharityStatusAPI`
- keep those packages as thin shims only
- add any new capability naming under `verification_platform`
- keep `charity_status` working until a later deprecation/removal phase is explicitly planned

## Future-Proofing Benefits

This approach reduces future rename cost because:

- product-brand changes do not require immediate package renames
- capability boundaries become clearer before any code movement
- later migration phases can move implementations behind stable capability wrappers
- split-repo or package-extraction work can converge on neutral domains without breaking existing import paths first

## Later Rename Risks

The biggest risk areas for later rename phases are still:

- deep internal imports across `charity_status.*` modules
- path-sensitive packaging and extraction work in `public-core/` and `private-platform/`
- docs and generated artifacts that still mention the repository name explicitly
- duplicated scaffolding under `frontend/` that mirrors current package naming

Those later phases should be handled separately from this abstraction layer.
