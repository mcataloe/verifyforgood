# Charity Status API

Charity Status API ingests IRS Exempt Organizations data and Form 990 XML-derived datasets into AWS, then serves nonprofit verification and scoring via Lambda + API Gateway.

## Current Architecture

- Runtime: Python 3.11
- Infrastructure: Terraform
- Compute: AWS Lambda
- API: API Gateway (`GET /nonprofit/{ein}`, `GET /nonprofit/{ein}/filings`, `GET /nonprofits/search`, `GET /nonprofits/{ein}/sources`, `GET /nonprofits/{ein}/sources/{source_name}`, `GET /nonprofits/{ein}/compliance`, `GET /nonprofits/{ein}/federal-awards`, `POST /verify`, `POST /verify/batch`)
- Data lake: S3 + Glue Catalog + Athena
- Serving cache: DynamoDB materialized nonprofit profiles (lazy read-through)

## Public-Core Boundary (Phase 11A)

Phase 11A introduces explicit separation boundaries so domain logic can remain canonical/open while deployment/platform wiring can be isolated.

Core/domain modules (intended reusable/public surface):

- `charity_status/query`, `charity_status/scoring`, `charity_status/decision`, `charity_status/evidence`, `charity_status/policy`
- new core interfaces in `charity_status/core/`:
  - `QueryRepository`
  - `ProfileStoreAdapter`
  - `EnrichmentProviderGateway`
  - `AuthContextProvider`
  - `QuotaMeteringHook`

Platform/runtime wiring (environment/deployment concerns):

- `charity_status/platform/runtime.py` builds concrete Athena and enrichment adapters from env/runtime config
- Lambda entrypoints consume these boundaries while keeping handlers thin

Contributor guidance:

- Keep business rules and deterministic domain logic inside core/domain packages.
- Keep provider/env/runtime selection in platform wiring modules.
- Route handlers should orchestrate only; avoid source-specific or provider-specific business logic in handlers.
- If adding auth/quotas, implement adapters behind `AuthContextProvider` and `QuotaMeteringHook` first, then inject.

## Repo Split Scaffolding (Phase 11B)

Phase 11B adds non-breaking scaffolding to make a future public/private split low risk while keeping this repository fully functional today.

New top-level scaffold directories:

- `public-core/` (future open-source packaging boundary)
- `private-platform/` (future proprietary platform boundary)
- `infra-deployment/` (future deployment-only boundary)

Migration planning artifacts:

- `split-plan.json`: machine-readable include/exclude mapping for split execution
- `docs/repo-split-guide.md`: what belongs in public vs private vs infra repos

Important:

- No proprietary code is removed automatically in this phase.
- Existing runtime and tests continue to use current paths.
- Core packaging metadata is prepared in `public-core/pyproject.toml` for extraction planning.

## AWS Data Flow

1. `lambda_ingest.py` downloads IRS EO CSV files (`eo1.csv`-`eo4.csv`) into S3.
2. `lambda_form990.py` ingests Form 990 index/XML and writes normalized JSONL datasets.
3. Glue catalogs EO/BMF and Form 990 normalized datasets.
4. `lambda_query.py` handles verification/scoring endpoints.
5. For `GET /nonprofit/{ein}`, Lambda uses DynamoDB read-through serving:
   - check materialized profile in DynamoDB
   - return cached profile on hit
   - on miss, run Athena/source assembly path, materialize to DynamoDB, return response

## Form 990 Datasets

S3 prefixes (configurable via Terraform variables):

- raw IRS source artifacts: `form990/raw-sources/`
- raw XML: `form990/raw/`
- normalized filings: `form990/normalized/metadata/`
- derived metrics: `form990/normalized/metrics/`
- governance flags: `form990/normalized/governance/`
- filing quality: `form990/normalized/quality/`
- manifests: `form990/normalized/manifests/`

Operational note:

- `lambda_form990` processes explicit `records[]` input, or (when `records` is omitted) can fetch records from configured IRS index URLs (`FORM990_INDEX_URL` / `FORM990_INDEX_URLS`).
- `lambda_form990` now defaults to repo-backed source-catalog discovery (`FORM990_SOURCE_MODE=static_manifest`), which reads the checked-in [`infrastructure/charity_status/form990/Form990Links.txt`](infrastructure/charity_status/form990/Form990Links.txt) manifest for known yearly CSV/ZIP artifacts.
- `FORM990_SOURCE_MODE=configured` remains available for manual source catalogs and index URLs, and `FORM990_SOURCE_MODE=irs_page` remains available only as a legacy compatibility path.
- static discovery can also synthesize one next-year TEOS source set from the latest explicit TEOS year in the manifest so the pipeline can keep pace when the checked-in manifest lags by one year.
- If neither explicit records nor index URLs are provided, the default discovery path runs against the repo-backed static manifest.
- Raw XML download defaults to `FORM990_DEFAULT_DOWNLOAD_RAW=true` unless overridden per invocation with `download_raw`.

Current discovery-stage architecture:

- supports `mode=bootstrap` and `mode=incremental` (default).
- normal runtime discovery is deterministic and repo-backed; it normalizes the static manifest into the same source artifact catalog previously used for configured sources and IRS-page links.
- the static manifest is authoritative because scraping/parsing the IRS downloads HTML page proved unreliable for newest-year discovery.
- source artifacts capture:
  - source year
  - source kind (`csv_index` or `zip_archive`)
  - source URL
  - source filename
  - logical archive key
  - discovery timestamp
  - source signature
  - optional source etag / last-modified
  - page URL
- discovery persists:
  - latest discovery state
  - per-run discovery catalog manifests
  - per-run discovery diff manifests
- raw source persistence stores original IRS artifacts unchanged under a dedicated prefix separate from extracted filing XML.
- raw source object keys preserve history by including stable source identity plus source signature; the bucket does not rely on S3 versioning for historical retention.
- latest downloaded-source state is stored as per-source state entries so the pipeline can skip already persisted artifacts with unchanged signatures.
- source diffs classify:
  - new sources
  - removed sources
  - changed sources
  - unchanged sources
- inline mode downloads required raw ZIP/CSV artifacts immediately after discovery.
- orchestrated mode queues raw source download work items instead of filing-ingest chunks.
- this phase intentionally stops before:
  - CSV filing reconciliation
  - ZIP member extraction
  - normalized filing parsing from discovered source artifacts

Known supported discovery filename patterns include:

- `index_{year}.csv`
- `{year}_TEOS_XML_01A.zip`
- `{year}_TEOS_XML_11B.zip`
- `{year}_TEOS_XML_11C.zip`
- `{year}_TEOS_XML_11D.zip`
- `{year}_TEOS_XML_CT1.zip`
- `download990xml_{year}_{n}.zip`

Later phases will extend the same flow to:

- reconcile CSV index catalogs
- extract selected filings from ZIP archives
- parse and normalize filing XML

Historical notes on the pre-refactor filing-stage flow:

- older discovery-mode behavior fetched filing-level records immediately after discovery.
- persists:
  - explicit-record and legacy direct-ingest manifests still follow the existing filing-manifest flow when those entry paths are used.

Phase 10G scheduling/reconciliation hardening:

- policy-driven target-year selection with explicit modes:
  - `bootstrap`
  - `incremental`
  - reconciliation (policy-driven full-year source discovery when due)
- incremental defaults to scanning current + previous year (`form990_incremental_year_window=2`)
- configurable reconciliation cadence (`form990_reconciliation_cadence_days`) and enablement toggle
- explicit target-year override supported (`form990_target_years`)
- safe fallback behavior when year metadata is missing/malformed
- no-op behavior remains deterministic when discovery state is unchanged
- policy metadata is included in run output and ops run visibility for diagnostics

Recommended schedules:

- production:
  - daily incremental ingest (current + previous year)
  - periodic reconciliation every 30 days over all discovered years
- non-production:
  - less frequent incremental schedule (for example every few days)
  - reconciliation disabled or manual-only unless explicitly needed

Operational run guidance:

- initial bootstrap:
  - run `mode=bootstrap` with the default `source_mode=static_manifest` (or omit `source_mode`)
  - verify discovery/source-download/filing manifests are written before enabling scheduled runs
  - expect larger first-run ZIP extraction and normalization volume
- incremental cadence:
  - run `mode=incremental` daily (or equivalent cadence) with current+previous year window
  - let CSV reconciliation select only new/changed/incomplete filings
- reconciliation behavior:
  - periodic reconciliation should be enabled for full-year drift correction
  - reconciliation updates filing state for inspected years while preserving other years
- raw source storage strategy:
  - preserve historical raw IRS ZIP/CSV copies via object key strategy
  - do not rely on S3 versioning for raw IRS source retention
- failure and retry expectations:
  - transient source/XML download failures are retried automatically
  - malformed ZIP/XML and ZIP-member misses are recorded explicitly
  - worker chunk retries are resumable; succeeded chunks are short-circuited to avoid duplicate processing

Filing-level reconciliation now runs after raw source persistence:

- yearly CSV indexes are the authoritative filing catalog for incremental Form 990 selection
- the reconciler reads the downloaded raw CSV artifacts from S3 and diffs filing rows against latest filing state
- only new, changed, or incomplete filings are selected for downstream ingest
- selected filings are resolved against raw ZIP source artifacts in S3 and extracted from ZIP members as the primary XML path
- direct `xml_url` download is used only as fallback when ZIP-member resolution fails and a trustworthy URL is available
- historical source retention still comes from object keys/manifests, not S3 versioning

Phase 10G ZIP discovery/reconciliation extension:

- source modes:
  - `static_manifest` (default): parse the checked-in `infrastructure/charity_status/form990/Form990Links.txt` manifest
  - `configured`: normalize caller- or env-provided manual source catalogs/index URLs
  - `irs_page`: legacy/deprecated compatibility mode that discovers yearly links from `FORM990_IRS_DOWNLOADS_PAGE_URL`
- static-manifest validation:
  - runtime fails fast if the packaged `Form990Links.txt` manifest is missing or cannot be parsed into supported CSV/ZIP source artifacts
- static-manifest next-year behavior:
  - when enabled, the parser clones only the latest explicit TEOS-era year into a single next year
  - example: if `2025` is the highest explicit TEOS year, the runtime also synthesizes `2026` `index_2026.csv` plus the matching `2026_TEOS_XML_*` ZIP set
  - generated entries are marked with `generated://form990-next-year/...` in `page_url` so they remain backward-compatible but distinguishable from explicit manifest rows
  - disable with `FORM990_ENABLE_NEXT_YEAR_GENERATION=false` / Terraform `form990_enable_next_year_generation = false`
- discovery keeps multiple source artifacts per year rather than collapsing to a single yearly link
- discovery captures per-source metadata:
  - source year
  - source kind
  - source URL
  - source filename
  - source archive key
  - source page URL
  - discovery timestamp
  - source signature / page etag / last-modified (when available)
- discovery state is persisted separately from filing-manifest state:
  - discovery state: `form990/normalized/manifests/discovery/state/latest_sources.json`
  - discovery run manifest: `form990/normalized/manifests/discovery/runs/{run_id}/catalog.json`
  - discovery diff manifest: `form990/normalized/manifests/discovery/runs/{run_id}/diff.json`
- raw source downloads are persisted separately from extracted filing XML:
  - raw IRS source artifacts: `form990/raw-sources/{year}/{source_kind}/{archive_key}/{source_signature}/{filename}`
  - downloaded-source state: `form990/normalized/manifests/source-download/state/latest/{year}/{source_kind}/{archive_key}.json`
  - source download manifests: `form990/normalized/manifests/source-download/runs/{run_id}/batch_{batch_index}.json`
- versioning note:
  - raw IRS source history is preserved by object key strategy and manifests
  - S3 bucket versioning is intentionally not used for these large ZIP/CSV artifacts to avoid duplicate-version storage bloat
- current incremental behavior:
  - detect source changes at discovery layer
  - select target years for source and filing work
  - download only source artifacts missing from downloaded-source state or changed by source signature
  - reconcile filing rows from the downloaded yearly CSV indexes
  - resolve selected filings to ZIP members and extract only required XML entries where feasible
  - parse only selected filing XML and persist normalized outputs
  - use URL fallback only when ZIP resolution cannot locate the filing XML

"Already on file" now means the latest filing state contains a complete terminal outcome for that filing:

- `parsed` filings are complete only when filing state records the normalized dataset artifact keys written by ingest
- `unsupported_return_type` is treated as a terminal complete outcome when recorded in filing state
- `index_only`, failed, or missing-artifact states are incomplete and are re-selected on later CSV reconciliation runs

Phase 10H parallel chunk processing:

- execution modes:
  - `inline` (existing single-invocation processing)
  - `orchestrated` (SQS chunking + worker Lambdas)
- orchestrated flow:
  - orchestrator discovers sources, reconciles CSV filings, and writes selected filing chunks to S3
  - orchestrator enqueues chunk messages to SQS
  - worker Lambda processes selected filings using ZIP-backed extraction first, then URL fallback when needed
  - per-run/per-chunk artifacts are persisted under:
    - `ops/form990-runs/{run_id}/run.json`
    - `ops/form990-runs/{run_id}/chunks/{chunk_id}.json`
    - `ops/form990-runs/{run_id}/results/{chunk_id}.json`
    - `ops/form990-runs/{run_id}/summary.json`
- retries/failures:
  - worker failures leave SQS messages unacked for retry
  - after max receives, messages move to DLQ
  - run metadata includes `chunk_status_counts` (`queued`, `running`, `succeeded`, `failed`, `dlq`)

## Phase 10E: Post-Ingest Incremental Refresh

After 10D ingestion identifies and processes new/changed filings, post-ingest refresh can rebuild materialized nonprofit serving profiles only for affected EINs.

Flow:

1. ingest run produces `run_id`, `affected_eins`, and `affected_filing_ids`
2. refresh orchestration links `ingest_run_id` to `refresh_run_id`
3. for each affected EIN, canonical verification/scoring/evidence/policy pipeline recomputes profile
4. materialized writer updates DynamoDB only when profile hash/version changed
5. structured change events are emitted for materially changed profiles

Run metadata includes:

- `refresh_run_id`
- `ingest_run_id`
- `started_at` / `completed_at`
- `affected_ein_count`
- `refreshed_count`
- `unchanged_count`
- `failed_count`
- `mode` / `environment`

Per-EIN metadata includes:

- `ein`
- `trigger_reason`
- `source_filing_ids`
- `previous_profile_hash` / `new_profile_hash`
- `changed`
- `status`
- `error` (when failed)

Behavioral guarantees:

- incremental: only affected EINs are refreshed
- idempotent: unchanged reruns are recognized and skipped
- failure isolation: one EIN failure does not fail entire refresh run

Glue tables:

- `form990_metadata`
- `form990_metrics`
- `form990_governance`
- `form990_quality`

## Extracted 990 Fields (Phase 4B)

Financial fields:

- `total_revenue`
- `total_expenses`
- `program_service_expenses`
- `management_general_expenses`
- `fundraising_expenses`
- `contributions_revenue`
- `total_assets_eoy`
- `total_liabilities_eoy`
- `net_assets_eoy`
- `grants_paid`
- `officer_compensation`

Governance indicators:

- `independent_board_majority`
- `conflict_of_interest_policy`
- `whistleblower_policy`
- `records_retention_policy`
- `contemporaneous_board_minutes`
- `material_diversion_reported`
- `compensation_review_process`
- `public_disclosure_available`
- `audited_financials_indicator`

Narrative/disclosure signals:

- mission description present
- program accomplishments present
- leadership disclosed
- missing narrative sections list

Derived metrics:

- `programExpenseRatio`
- `adminExpenseRatio`
- `fundraisingRatio`
- `liabilitiesToAssetsRatio`
- `operatingMargin`
- `fundraisingEfficiency`
- `workingCapital`
- `monthsOfRunway`

## Relationship Graph Foundation (Phase 9A)

Form 990 ingestion now emits additive relationship-edge artifacts (JSONL) for future network/risk analysis, without introducing a graph database.

Current edge types:

- `PERSON_TO_NONPROFIT_OFFICER`
- `PERSON_TO_NONPROFIT_BOARD`
- `NONPROFIT_TO_STATE`

Design notes:

- identity resolution is conservative (`PERSON#{ein}#{normalized_name}`) to avoid over-merging across nonprofits
- duplicate edges are suppressed deterministically
- artifacts are stored under `form990/normalized/relationships/` for future Athena querying or graph import
- existing ingestion and verification flows remain unchanged/failure-tolerant

Filing quality indicators:

- `missingRequiredFieldsCount`
- `internalConsistencyIssuesCount`
- `staleFilingDays`
- `narrativeMissing`
- `anomalyFlags`
- `scoreConfidence`

## Scoring (Phase 4C)

Model version: `1.1.0`

Scoring modes:

- EO/BMF-only fallback (`irs_eo_bmf_athena`)
- EO/BMF + 990 enrichment (`irs_eo_bmf_athena`, `irs_form_990_xml`)

Dimensions:

- `compliance`
- `trust`
- `financial_resilience`
- `transparency`
- `overall`

Hard rules:

- If status is not active, eligibility is `INELIGIBLE` and overall score is capped conservatively.
- If revoked hard-rule conditions are present, eligibility is `INELIGIBLE` and overall cap is stricter.
- Missing 990 data never fails requests; scoring falls back and explanation states EO/BMF-only mode.
- Missing optional third-party vendor data does not change score calculation or deny the organization by default.
- Third-party integration policy is surfaced additively in `score_explanation.integration_policy`; scoring remains neutral unless a required integration or explicit customer policy changes the recommendation.

## External Enrichments (Phase 5A)

External enrichments are optional and source-attributed. Core verification/scoring still works using IRS EO/BMF + 990 data only.
Current external source framework is explicitly scoped to U.S. nonprofits.

Framework location:

- `infrastructure/charity_status/enrichments/base.py`
- `infrastructure/charity_status/enrichments/registry.py`
- `infrastructure/charity_status/enrichments/service.py`
- `infrastructure/charity_status/enrichments/providers/`
- `infrastructure/charity_status/sources/`

Included providers:

- `mock_provider`: deterministic test provider
- `candid`: scaffolded provider module with safe fallback behavior
- `state_registry_mock`: deterministic state compliance mock provider
- `state_registry`: scaffolded adapter-based provider for future state-specific registries

Response behavior:

- Query responses may include:
  - `enrichment.providers[]` with provider-specific normalized fields for attempted integrations only
  - `enrichment.failures[]` for provider call failures
  - `integration_evaluation.integrations[]` with logical integration availability and requirement state
  - `integration_evaluation.attempted_integrations[]`
  - `integration_evaluation.used_integrations[]`
  - `integration_evaluation.required_unmet_integrations[]`
  - `integration_evaluation.explanations[]` with explicit explanation entries for platform availability, organization enablement, optional skips, required-unavailable states, and successful evaluations
  - `score_explanation.integration_policy` with summary status/counts plus the evaluation explanations
- Provider errors, integrations not offered by the deployment, organization-disabled integrations, missing credentials, or no matches do not fail core nonprofit verification by default unless the integration is explicitly required or a customer policy acts on those signals.
- Missing third-party vendor data is neutral unless the organization explicitly marks that integration as required for eligibility evaluation.

Default evaluation policy behavior:

- platform integration not offered: ignored with zero effect
- integration offered but disabled for the organization: ignored with zero effect
- integration enabled but optional: missing vendor data is informational only and does not cause denial or score penalty
- integration enabled and required: unavailable/no-match vendor data can downgrade the default decision to `manual_review`, and customer policy may further act on that state explicitly
- successful integration evaluation: available third-party data is reflected in the explanation output and any source-specific summaries

Canonical enrichment fields are optional and include source attribution:

- `transparency_level`
- `profile_complete`
- `external_rating_label`
- `rating_score`
- `impact_metrics_available`
- `leadership_data_present`
- `profile_link`

State compliance enrichment fields (when available):

- `registration_status`
- `registration_jurisdiction`
- `registration_expiration_date`
- `solicitation_permitted`
- `compliance_flags`

Configuration (Terraform variables):

- `third_party_integrations_enabled`
- `integration_candid_enabled`
- `integration_candid_client_id`
- `integration_candid_client_secret`
- `integration_charity_navigator_enabled`
- `integration_charity_navigator_api_key`
- `default_require_candid_for_evaluation`
- `default_require_charity_navigator_for_evaluation`
- `organization_integration_settings_json`
- `enrichment_mock_offered`
- `enrichment_mock_enabled`
- `enrichment_candid_offered`
- `enrichment_candid_enabled`
- `enrichment_candid_endpoint`
- `enrichment_candid_api_key`
- `enrichment_timeout_seconds`
- `enrichment_state_registry_offered`
- `enrichment_state_registry_enabled`
- `enrichment_state_registry_mock_enabled`
- `enrichment_state_business_offered`
- `enrichment_state_business_enabled`
- `enrichment_state_business_mock_enabled`
- `enrichment_usaspending_offered`
- `enrichment_usaspending_enabled`
- `enrichment_usaspending_mock_enabled`
- `enrichment_ofac_offered`
- `enrichment_ofac_enabled`
- `enrichment_ofac_mock_enabled`
- `tenant_integration_settings_json` (legacy alias)

Recommended Lambda environment variables for the new normalized platform model:

```text
THIRD_PARTY_INTEGRATIONS_ENABLED=false

INTEGRATION_CANDID_ENABLED=false
INTEGRATION_CANDID_CLIENT_ID=
INTEGRATION_CANDID_CLIENT_SECRET=

INTEGRATION_CHARITY_NAVIGATOR_ENABLED=false
INTEGRATION_CHARITY_NAVIGATOR_API_KEY=

DEFAULT_REQUIRE_CANDID_FOR_EVALUATION=false
DEFAULT_REQUIRE_CHARITY_NAVIGATOR_FOR_EVALUATION=false
```

Organization integration settings are env-backed JSON keyed by `workspace_id` with `account_id` fallback:

```json
[
  {
    "workspace_id": "ws_123",
    "account_id": "acct_123",
    "integrations": {
      "candid": { "enabled": true, "requiredForEvaluation": false },
      "charityNavigator": { "enabled": false, "requiredForEvaluation": false }
    }
  }
]
```

Resolution defaults:

- no integrations enabled
- no integrations required
- no third-party provider calls attempted unless both the deployment offers the integration and the tenant enables it
- credential presence does not enable an integration
- enabling an integration does not require it for evaluation

## U.S. Source Catalog (Phase 10A)

The enrichment framework now includes a typed U.S.-only source catalog domain model that classifies external source capabilities and normalized source records.

Source categories:

- `identity`
- `compliance`
- `financial`
- `federal_awards`
- `risk`
- `transparency`

Typed source model components:

- source metadata
- normalized source records
- source attribution
- source freshness/retrieval timestamps
- provider capability classification

Provider extension guidance:

- implement provider logic under `charity_status/enrichments/providers/`
- expose provider capabilities via `capabilities()`
- return normalized `source_records` alongside existing enrichment fields
- keep provider-specific schemas out of business logic; map into normalized source records
- keep U.S.-only behavior explicit unless a future phase expands scope

## Public U.S. Source Adapters (Phase 10B)

Phase 10B adds initial public U.S. source-family adapters (framework + deterministic mocks + scaffolded concrete adapter shapes):

- state charity registry compliance
- state business entity / secretary-of-state status
- USAspending federal awards
- OFAC sanctions screening

Behavior:

- source results are normalized into typed `source_records` with attribution/freshness metadata
- provider capability metadata is exposed via the source catalog
- provider failures/unavailable data remain non-fatal
- existing enrichment payload shape remains backward compatible (`providers` + `failures` still present)

Integration:

- `evidence` now includes sanctions/federal-awards risk visibility factors
- `policy` supports hooks such as sanctions match, minimum federal awards, and state business status filters
- decision/audit risk context includes sanctions and state business status indicators where available

Contributor guidance:

- implement adapters behind provider interfaces (avoid leaking provider schema outside provider module)
- map provider-specific fields into normalized source records
- keep logic deterministic and U.S.-scoped in this phase
- avoid scraping-heavy patterns unless isolated and explicitly justified

Failure tolerance:

- State registry provider failures/unavailable records do not fail core verification.
- Normalized compliance output is included as `state_compliance` when available and feeds evidence/policy/decision risk context.

## State Registry Framework (Phase 11A)

Phase 11A adds a dedicated state-registry framework under `charity_status/state_registry/` for future U.S. business-registry ingestion and query work.

Package layout:

- `models.py`: canonical lookup and normalized record dataclasses
- `enums.py`: practical constrained values for source type, entity status, standing, and confidence
- `contracts.py`: shared adapter contract for search, optional fetch-by-id, and raw-to-canonical parsing
- `registry.py`: explicit adapter registration and resolution by state code
- `normalization.py`: shared name/status/standing normalization helpers plus stable raw-payload hashing
- `matching.py`: shared matching primitives kept separate from source-specific parsing
- `traceability.py`: raw payload reference helpers for retrieval timestamp, hash, parser version, and optional storage locator
- `adapters/`: state-specific implementations isolated per state module

Canonical normalized record fields:

- `state_code`
- `source_name`
- `source_type`
- `external_entity_id`
- `entity_name`
- `normalized_entity_name`
- `entity_type`
- `status`
- `standing`
- `formation_date`
- `dissolution_date`
- `last_filing_date`
- `registry_url`
- `raw_fetched_at`
- `raw_hash`
- `parser_version`
- `matched_on`
- `confidence`
- `raw_payload_ref`

Extension rules for new states:

- add each state under its own module in `charity_status/state_registry/adapters/`
- keep source-specific field names and parsing logic inside that state module only
- map all outputs into the shared `StateRegistryRecord` contract before other application layers see them
- reuse shared normalization, matching, and traceability helpers instead of copying them into state modules
- register adapters explicitly via `StateRegistryAdapterRegistry`; unsupported states must fail cleanly

Design intent:

- the contract supports both search-portal style registries and bulk dataset sources
- fetch-by-external-id is optional and should raise a clear unsupported-operation error when a state does not provide it
- raw payload traceability is part of the canonical model so source records can be audited and reprocessed later without leaking state-specific schema into shared logic

## Colorado State Registry Pilot (Phase 11B)

Phase 11B validates the shared framework with the first real state implementation under `charity_status/state_registry/adapters/colorado/`.

Colorado module layout:

- `client.py`: transport for the official Colorado business-entities dataset (`data.colorado.gov/resource/4ykn-tg5h.json`)
- `mapper.py`: Colorado-owned field mapping and status/standing normalization into the canonical record model
- `adapter.py`: shared-framework adapter implementation
- `__init__.py`: explicit exports only

Colorado implementation notes:

- source type is modeled as `bulk_dataset` because the integration is dataset-backed even though the adapter queries it over HTTP
- the adapter supports both name-based search and follow-up fetch by `entityid`
- Colorado-specific cleanup stays local to the mapper, including stripping status suffixes from dissolved entity names and translating `entitystatus` values into canonical status/standing values
- the canonical `registry_url` is built from the official Colorado Secretary of State detail route using the source `entityid`

Fixture and test guidance for future states:

- add realistic source samples under `tests/fixtures/state_registry/<state>/`
- keep fixture assertions focused on canonical output, not every raw source column
- do not use live network calls in unit tests; transport tests should stub HTTP responses
- malformed source rows should be ignored or fail cleanly inside the state-owned parser/mapper without affecting shared framework code

Shared lookup path:

- `StateRegistryLookupService` resolves the correct adapter by state code
- `search()` returns canonical `StateRegistryRecord` instances
- `fetch_by_external_entity_id()` uses the same parser path for follow-up retrieval when the state supports it

## Kentucky State Registry Validation (Phase 11C)

Phase 11C adds a second real adapter under `charity_status/state_registry/adapters/kentucky/` to validate the framework against Kentucky’s tab-delimited bulk company files.

Kentucky module layout:

- `client.py`: acquisition of the raw company snapshot text
- `parser.py`: tab-delimited company-file parsing plus composite external-id generation
- `mapper.py`: Kentucky-owned status, standing, entity-type, and date mapping
- `adapter.py`: shared-contract adapter wiring with local bulk snapshot caching

Kentucky source notes:

- the official SOS business files are documented as tab-delimited bulk files
- the business record identity is the composite of `ID`, `comptype`, and `compseq`
- Kentucky parsing keeps raw acquisition separate from row parsing so future batch refresh/orchestration can reuse the parser without embedding HTTP concerns

Framework validation outcome:

- no shared contract break was required after adding the second Tier 1 adapter
- the existing `search()` and `fetch_by_external_entity_id()` contract was sufficient for both dataset-backed Colorado and bulk-file Kentucky
- the practical rule for future Tier 1 bulk adapters is:
  - keep transport, parser, and mapper separate inside the state module
  - generate canonical external ids from the source’s true record identity when a single source column is not enough
  - keep source-specific code tables local to the state mapper

Fixture guidance for future bulk-data states:

- include realistic tabular snapshots under `tests/fixtures/state_registry/<state>/`
- cover ambiguous candidate scenarios when one legal entity can surface multiple historical/company-sequence rows
- assert parser-version and raw-payload traceability fields for at least one canonical record
- malformed rows should fail locally in the state parser/mapper and not require shared framework exceptions

## Peer Benchmarking (Phase 5B)

Model version `2.0.1` adds optional peer-group benchmarking for fairer interpretation of selected metrics and normalizes alternate IRS status code formats before scoring/materialization.

Peer-group dimensions:

- NTEE group (first character when available)
- organization type/subsection when available
- revenue band:
  - `under_250k`
  - `250k_to_1m`
  - `1m_to_10m`
  - `10m_to_100m`
  - `100m_plus`
- optional state in peer grouping payload

Peer benchmarking behavior:

- Uses peer context only when peer group size meets minimum threshold.
- If peer data is sparse/unavailable, scoring falls back to deterministic threshold-based logic.
- Response explanation includes:
  - `peer_group`
  - `peer_group_size`
  - `peer_benchmarking_used`
  - `benchmarked_metrics`

Benchmarked metrics (when peer data is sufficient):

- `program_expense_ratio`
- `liabilities_to_assets_ratio`
- `operating_margin`
- `months_of_runway`

The model remains deterministic and auditable; no black-box ML is used.

## Decision Workflow (Phase 5C)

Responses now include deterministic decisioning fields for CSR/donation-matching workflows:

- `decision`
- `audit`
- `summary`

Decision statuses:

- `approve`
- `approve_with_review`
- `manual_review`
- `deny`
- `insufficient_data`

`decision` includes:

- `status`
- `reasons`
- `risk_flags`
- `next_actions`
- `manual_review.reason_codes`
- `manual_review.notes`
- `manual_review.flags`

Manual review trigger examples:

- EIN/name mismatch
- missing or stale filing confirmation
- missing governance disclosures
- enrichment provider failures/conflicts
- low-confidence scoring signals
- inactive/revoked status (which may escalate to `deny`)

Auditability fields:

- data sources used
- score model version
- material factors
- peer benchmarking usage/context
- enrichment usage
- decision basis (eligibility, overall score, reason codes)

Convenience export shape:

- `summary` contains `ein`, `organization_name`, `eligibility_status`, `overall_score`, `decision_status`

This is additive and does not replace detailed response fields.

## Structured Evidence (Phase 6A)

Responses now include a deterministic `evidence` object designed for explainability and audit reuse across live API responses and DynamoDB materialized profiles.

`evidence` shape:

- `factors[]`: normalized positive/negative/warning signals
- `sources[]`: source usage records (EO/BMF, Form 990, enrichment providers/failures)
- `rule_results[]`: deterministic rule outcomes used for explainability
- `confidence`: inherited from score explanation confidence
- `generated_at`: UTC timestamp when evidence was generated
- `model_version`: score model version used to generate evidence

Evidence signals cover:

- eligibility/compliance
- financial resilience
- transparency
- governance/quality
- peer benchmarking usage
- enrichment usage/failures when relevant

Compatibility notes:

- Existing fields (`scores`, `score_explanation`, `decision`, `audit`, `summary`) remain unchanged.
- `evidence` is additive and available in:
  - `GET /nonprofit/{ein}`
  - `POST /verify`
  - DynamoDB materialized profile records and cache-hit responses

## API Endpoints

## Authentication and Quotas (Phase 12A)

API key auth is supported for server-to-server and developer workflows, designed to coexist with future OAuth.

Header:

- `x-api-key: csk_<key_id>.<secret>`
- `Authorization: Bearer <oauth_access_token>` (OAuth 2.1 client-credentials style M2M)

Key model:

- key prefix/id + secret pattern
- secrets are stored as hashes (`secret_hash`), not plaintext
- one-time secret display is supported by generation contracts in `charity_status/auth/service.py`
- key is associated with `account_id` and `workspace_id`
- key may include scopes/entitlements and plan assignment

Plan model (initial):

- `developer`: 250 requests/month
- `starter`, `team`, `business`, `enterprise`: placeholder limits

Quota enforcement:

- deterministic monthly quota checks run before endpoint execution
- usage is metered through auth/quota hooks and principal context abstraction
- over-limit requests return `429`

Terraform/env settings:

- `api_auth_enabled`
- `api_key_records_json`
- `oauth_m2m_enabled`
- `oauth_token_records_json`
- `organization_integration_settings_json`
- `tenant_integration_settings_json` (legacy alias)

Local dev note:

- keep `api_auth_enabled=false` for unrestricted local testing, or provide `api_key_records_json` with hashed secrets for auth-enabled testing.
- key generation contract (one-time secret display + hashed-at-rest record) is available via `charity_status.auth.build_api_key_record`.
- OAuth token record generation contract is available via `charity_status.auth.build_oauth_token_record`.

Auth coexistence behavior:

- when OAuth M2M is enabled, requests with `Authorization: Bearer ...` use OAuth token auth
- otherwise requests fall back to API key auth (`x-api-key`)
- both auth modes resolve to a shared principal/account/plan/scopes abstraction for consistent authorization and billing behavior

## Billing Domain Model (Phase 12B)

Billing/productization modeling is now available as deterministic domain types in `charity_status/billing/` (no external payment processor dependency yet).

Core billing entities:

- `Account` / `Workspace`
- `SubscriptionPlan`
- `EntitlementSet`
- `UsageMeter`
- `MonthlyQuotaPeriod`
- overage-ready accounting fields (`included_units`, `overage_unit_price_usd_micros`)

Default plans:

- `developer` (250/month)
- `starter`
- `team`
- `business`
- `enterprise`

Entitlement-driven feature gating:

- batch verification
- advanced source visibility
- monitoring/change-event capability hooks
- premium compliance/risk visibility

Deterministic metering hooks:

- single verification requests count as 1 unit
- batch verification meters by `items[]` count
- source visibility endpoints may consume higher unit weights

External model remains simple:

- API clients still see standard HTTP auth/quota behavior (`401`/`403`/`429`)
- richer usage and overage accounting is internal/domain-ready for future billing processor integration

### `GET /nonprofit/{ein}`

Returns normalized organization + verification + scores + model + score explanation.
When 990 data exists, includes enriched scoring factors and optional `filing_summary`.

### `GET /nonprofits/search`

Lightweight nonprofit listing/search endpoint (Athena-backed in this phase).

Query params:

- `q` (required): name query string
- `state` (optional): two-letter state filter
- `subsection` (optional): IRS subsection filter
- `active_only` (optional): boolean (`true`/`false`)
- `limit` (optional): page size (bounded by config)
- `cursor` (optional): opaque pagination token from prior response

Response shape is intentionally index-friendly and lightweight:

- `query`
- `pagination.limit`
- `pagination.next_cursor`
- `items[]` with summary fields (`ein`, `ein_normalized`, `name`, `state`, `subsection`, `irs_status`, `active`, `tax_period`)

### `GET /nonprofits/{ein}/sources`

Returns normalized source inspection output for the EIN, with source attribution and freshness metadata.

Response fields:

- `ein`
- `organization` (`ein`, `name`, `state`)
- `sources[]`:
  - `source_name`
  - `status` (`matched`, `no_match`, `missing_credentials`, `tenant_disabled`, `not_offered`, `failed`, etc.)
  - `normalized_data`
  - `attribution` (`record_id`, `licensed`, `notes`)
  - `freshness.retrieved_at`
  - `error` (when provider had an error)
  - `driver`
  - `tenant_enabled`
  - `required_for_eligibility`
  - `evaluation_effect` (`neutral`, `warning`, `positive`)
  - `explanation_code`
  - `explanation`
- `failures[]` (provider-level failures from enrichment run)

### `GET /nonprofits/{ein}/sources/{source_name}`

Returns one normalized source entry for the EIN.

- `404` when source is unsupported/not present for that EIN
- `200` with `source` payload when available
- Legacy `_mock` source aliases are still accepted for direct lookups, but logical source names are returned in collection responses.

### `GET /nonprofits/{ein}/compliance`

Returns compliance visibility summary aggregated from normalized source records (for example, state registry + state business).

Response fields:

- `ein`
- `compliance`:
  - `registration_status`
  - `registration_jurisdiction`
  - `registration_expiration_date`
  - `solicitation_permitted`
  - `compliance_flags[]`
  - `state_business_status`
  - `state_business_good_standing`
  - `status` (`available` or `unavailable`)
- `sources[]` (normalized source entries used for summary)

### `GET /nonprofits/{ein}/federal-awards`

Returns normalized federal awards summary derived from external source records.

Response fields:

- `ein`
- `federal_awards`:
  - `award_count`
  - `total_obligations_usd`
  - `latest_award_date`
  - `status` (`available` or `unavailable`)
  - `source`

### `GET /organizations/integrations`

Returns the current organization-level third-party integration settings for the authenticated workspace/account context.

Response fields:

- `workspace_id`
- `account_id`
- `source` (`default` or `stored`)
- `updated_at` (when settings were previously persisted)
- `integrations.candid.enabled`
- `integrations.candid.requiredForEvaluation`
- `integrations.charityNavigator.enabled`
- `integrations.charityNavigator.requiredForEvaluation`

Organizations without persisted settings return backward-compatible defaults:

- `enabled=false`
- `requiredForEvaluation=false`

### `PUT /organizations/integrations`

Updates organization-level third-party integration settings for the authenticated workspace/account context.

Request body:

```json
{
  "integrations": {
    "candid": {
      "enabled": true,
      "requiredForEvaluation": false
    },
    "charityNavigator": {
      "enabled": false,
      "requiredForEvaluation": false
    }
  }
}
```

Validation:

- `requiredForEvaluation=true` with `enabled=false` returns `400`; the API does not silently enable the integration
- unsupported integration ids return `400`
- omitted integrations preserve their current values; unspecified organizations continue to default to disabled/not required

## Operational Endpoints (Phase 10F)

Operational diagnostics are exposed on a separate read-only surface under `/ops/*`:

- `GET /ops/ingest/runs`
- `GET /ops/ingest/runs/{ingest_run_id}`
- `GET /ops/ingest/runs/{ingest_run_id}/filings`
- `GET /ops/refresh/runs`
- `GET /ops/refresh/runs/{refresh_run_id}`
- `GET /ops/refresh/runs/{refresh_run_id}/eins`
- `GET /ops/nonprofits/{ein}/pipeline-status`

Run lifecycle status meanings:

- ingest: `success`, `partial_success`, `failed`
- refresh: `completed`, `completed_with_errors`, `failed`

Operational diagnostics are structured and safe:

- secrets/tokens are not exposed
- error summaries are code-oriented and redacted where sensitive text is detected
- stack traces are not returned from ops responses

Common debugging workflow for stale nonprofit data:

1. check latest ingest runs (`/ops/ingest/runs`) and inspect run detail
2. inspect filing items for the ingest run (`/ops/ingest/runs/{id}/filings`)
3. inspect linked refresh run and EIN outcomes (`/ops/refresh/runs/{id}/eins`)
4. inspect nonprofit pipeline status (`/ops/nonprofits/{ein}/pipeline-status`) for latest materialized hash/timestamps and staleness indicators

### `POST /verify`

Request body:

```json
{
  "ein": "12-3456789",
  "name": "Optional nonprofit name",
  "policy_id": "optional_named_policy"
}
```

Performs the same verification workflow as GET and includes conservative name-match metadata.

### `POST /verify/batch`

Synchronous batch verification endpoint for CSR/finance workflows.

Request body:

```json
{
  "items": [
    { "ein": "12-3456789" },
    { "ein": "98-7654321", "name": "Example Org", "policy_id": "strict_manual" }
  ]
}
```

Behavior:

- each item is processed independently
- invalid rows return item-level errors without failing the whole batch
- duplicates are processed independently
- max batch size is enforced by `BATCH_VERIFY_MAX_SIZE` (Terraform: `batch_verify_max_size`)

Response shape:

- `batch_summary`
- `items[]`
- `batch_summary.counts_by_status`
- `batch_summary.counts_by_decision`
- `batch_summary.counts_by_error`

## Policy Engine (Phase 6B)

Phase 6B adds a deterministic, config-driven customer policy layer for CSR workflows without replacing core nonprofit scoring or decisioning.

Policy behavior:

- uses a global default policy when no `policy_id` is provided
- optionally applies named policies via `POST /verify` request body
- evaluates deterministic conditions against assembled verification payload
- keeps `decision` unchanged and adds `policy_evaluation` separately
- exposes `final_recommendation` (policy-aware recommendation)

Supported condition types include:

- eligibility status
- overall score thresholds
- stale filing days
- missing governance disclosures
- enrichment failures
- required integrations missing
- specific integration failures
- state/subsection/cause filters (when present)

Response additions:

- `policy_evaluation.policy_id`
- `policy_evaluation.result`
- `policy_evaluation.matched_rules[]`
- `policy_evaluation.overrides_decision`
- `policy_evaluation.final_recommendation`
- top-level `final_recommendation` (mirrors policy evaluation outcome)

## Score Weighting Profiles (Phase 8B)

Scoring now supports named deterministic weighting profiles for dimension aggregation without changing hard eligibility caps.

Supported profiles:

- `default_v1` (balanced)
- `compliance_heavy_v1`
- `transparency_light_v1`

Usage:

- `POST /verify` supports optional `weighting_profile` in request body.
- `GET /nonprofit/{ein}` supports optional `weighting_profile` query parameter.
- `POST /verify/batch` items may include optional `weighting_profile`.

Auditability:

- `score_explanation.weighting_profile` includes requested/applied profile, weights, and fallback metadata.
- `audit.weighting_profile` mirrors applied profile details.
- `evidence` includes weighting profile factors/rule results.

Invalid profile behavior:

- defaults to deterministic fallback profile (`default_v1`) with `fallback_applied=true` in explanation metadata.

### `GET /nonprofit/{ein}/filings`

Returns filing summaries:

- `tax_year`
- `form_type`
- `filing_date`
- `amended`
- `parse_status`

## Current Limitations

- Deterministic, rules-based scoring only; no black-box ML.
- No paid third-party enrichment providers integrated.
- `charity_navigator` is recognized as a logical tenant-configurable integration id, but no live adapter is implemented yet.
- Extraction is schema-tolerant and conservative; unavailable fields remain `null`.

## Local Development

### Install dependencies

```bash
pip install -r infrastructure/requirements.txt
pip install -r infrastructure/requirements-dev.txt
```

### Run tests

```bash
python -m pytest -q
```

### Local reference implementation (no Terraform required)

Run the reference script to execute core verification flow with in-memory repository data:

```bash
python infrastructure/local_reference.py
```

This demonstrates local use of domain logic without Terraform, API Gateway, or Lambda deployment wiring.

## Terraform Deployment Notes

- Query Lambda package includes query/normalization/scoring modules.
- Ingest and Form 990 Lambdas are packaged separately.
- Domain registration remains manual; Route53 hosted zone and records are managed by Terraform when enabled.
- DynamoDB table is provisioned for serving profiles (`pk = EIN#{ein}`, `sk = PROFILE#LATEST`).

Form 990 mode configuration additions:

- `form990_source_mode`: `static_manifest` (default), `configured`, or `irs_page` (legacy)
- `form990_enable_next_year_generation`: enable or disable one-year-ahead TEOS source synthesis for static-manifest discovery
- `form990_irs_downloads_page_url`: IRS discovery page URL used only for legacy `irs_page` mode
- `form990_zip_fetch_timeout_seconds`: ZIP download timeout
- `form990_zip_max_xml_file_size_bytes`: ZIP extraction safety limit
- `form990_execution_mode`: `inline` or `orchestrated`
- `form990_chunk_size`: records per SQS chunk item
- `form990_worker_timeout_seconds`: worker Lambda timeout
- `form990_worker_memory_size_mb`: worker Lambda memory
- `form990_worker_reserved_concurrency`: worker concurrency limit
- `form990_queue_visibility_timeout_seconds`: SQS visibility timeout
- `form990_queue_max_receive_count`: SQS retry attempts before DLQ
- `form990_queue_batch_size`: SQS event source batch size for worker

Lambda event examples:

Default static-manifest mode:

```json
{
  "mode": "incremental"
}
```

Manual configured mode:

```json
{
  "mode": "incremental",
  "source_mode": "configured",
  "source_catalog": [
    {
      "year": "2024",
      "index_url": "https://example.org/index_2024.csv"
    }
  ]
}
```

Legacy IRS-page discovery mode (compatibility only):

```json
{
  "mode": "incremental",
  "source_mode": "irs_page",
  "target_years": ["2024"],
  "batch_size": 25,
  "limit": 50
}
```

Orchestrated mode:

```json
{
  "mode": "incremental",
  "execution_mode": "orchestrated",
  "target_years": ["2024"],
  "chunk_size": 250
}
```

Safe dev smoke test:

```json
{
  "mode": "incremental",
  "target_years": ["2024"],
  "eins": ["123456789"],
  "limit": 5,
  "batch_size": 5
}
```

## Serving Layer (Phase D1)

DynamoDB now acts as a low-latency serving layer for final nonprofit profile responses.

Stored materialized fields include:

- organization
- verification
- scores
- score_explanation
- latest filing summary (if present)
- enrichment summary (if present)
- decision/summary/audit structures
- model_version
- source_hash
- materialized_at
- environment
- source_data_versions

Environment-aware behavior:

- Non-production (`env != prod`): no eager preload, lazy/on-demand materialization only.
- If DynamoDB is empty, request still works via Athena/source assembly.
- First request for an EIN may be slower; repeat requests are faster via DynamoDB hit path.
- Read-through GETs bypass stale cached profiles when the stored `model_version` lags the current scoring model version.

## Materialization Refresh (Phase D2)

Phase D2 adds a refresh/materialization pipeline that updates DynamoDB only when needed.

Core modules:

- `charity_status/serving/change_detection.py`
- `charity_status/serving/compare.py`
- `charity_status/serving/writer.py`
- `charity_status/serving/refresh.py`

Refresh execution:

- `lambda_refresh.py` is a thin orchestrator Lambda.
- It rebuilds the canonical nonprofit profile for each target EIN using the same verification/scoring pipeline.
- It materializes a new candidate item with deterministic `source_hash`.
- It reads the current DynamoDB profile and writes only when:
  - item is missing
  - `source_hash` changed
  - `model_version` changed
  - force refresh is enabled
- If hash and version match, the write is skipped.

Supported refresh modes:

- `refresh_changed`
- `backfill_missing`
- `refresh_hot`
- `force_refresh`

Changed-EIN inputs:

- explicit EIN list via event payload (`eins` or `eins_csv`)
- optional source-driven changed EINs (`changed_eins`) when source detection is enabled

Non-prod cost controls (`env != prod`):

- No eager bootstrap/full preload behavior.
- Default behavior does not run broad source-driven selection.
- Non-prod refresh is minimal by default and typically acts on explicitly provided EINs.
- Source-driven detection in non-prod requires explicit enablement (`source_detection_enabled=true`).

Terraform additions are intentionally minimal:

- optional refresh Lambda
- optional EventBridge schedule
- refresh env vars (mode, batch size, force flag, source detection flag)

This keeps DynamoDB write costs lower by avoiding rewrites for unchanged profiles while preserving deterministic, auditable serving records.

Refresh output now includes compact structured `change_events[]` for updated records (no external delivery yet). Each event captures deterministic change types such as:

- `eligibility_changed`
- `overall_score_threshold_crossed`
- `decision_status_changed`
- `new_risk_flags`
- `filing_freshness_threshold_crossed`
- `compliance_status_changed`
- `new_compliance_flags`

Example refresh excerpt:

```json
{
  "mode": "refresh_changed",
  "updated": 1,
  "change_events": [
    {
      "ein": "123456789",
      "change_types": ["decision_status_changed", "new_risk_flags"],
      "previous": {
        "eligibility": "ELIGIBLE",
        "overall_score": 78,
        "decision_status": "approve",
        "risk_flags": []
      },
      "current": {
        "eligibility": "ELIGIBLE",
        "overall_score": 62,
        "decision_status": "approve_with_review",
        "risk_flags": ["state_compliance_flags_present"]
      }
    }
  ]
}
```

## Production Bootstrap (Phase D3)

Phase D3 adds explicit `bootstrap_all` support for production eager materialization while keeping non-prod lazy by default.

`bootstrap_all` behavior:

- pages through the source nonprofit population (Athena EIN pagination)
- builds canonical profiles through existing verification/scoring logic
- writes to DynamoDB using existing deterministic `source_hash`/`model_version` comparison
- skips unchanged records, updates changed records, inserts missing records
- reports structured run summary fields:
  - `status`
  - `total_seen`
  - `inserted`
  - `updated`
  - `skipped`
  - `failed`
  - `started_at`
  - `completed_at`
  - `duration_ms`
  - `batch_count`

Environment gating:

- `APP_ENV=prod`: `bootstrap_all` is allowed.
- `APP_ENV!=prod`: `bootstrap_all` is blocked by default.
- Non-prod override requires explicit enablement (`bootstrap_nonprod_override=true`).

Large-volume safety:

- processing is page-based (`refresh_batch_size`)
- no full in-memory source preload
- optional checkpointing via `start_after_ein`/`bootstrap_start_after_ein`
- optional per-run cap via `bootstrap_max_batches_per_run` (returns `status=partial` with `next_cursor`)

Non-prod defaults remain low-cost:

- lazy/on-demand serving stays the default
- targeted/manual refresh modes still supported (`refresh_changed`, `backfill_missing`, explicit EIN lists)
- no automatic non-prod eager bootstrap
