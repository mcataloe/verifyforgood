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

- raw XML: `form990/raw/`
- normalized filings: `form990/normalized/metadata/`
- derived metrics: `form990/normalized/metrics/`
- governance flags: `form990/normalized/governance/`
- filing quality: `form990/normalized/quality/`
- manifests: `form990/normalized/manifests/`

Operational note:

- `lambda_form990` processes explicit `records[]` input, or (when `records` is omitted) can fetch records from configured IRS index URLs (`FORM990_INDEX_URL` / `FORM990_INDEX_URLS`).
- If neither explicit records nor index URLs are provided, the run is successful but processes `0` records.
- Raw XML download defaults to `FORM990_DEFAULT_DOWNLOAD_RAW=true` unless overridden per invocation with `download_raw`.

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
  - `enrichment.providers[]` with provider-specific normalized fields
  - `enrichment.failures[]` for provider call failures
- Provider errors, disabled providers, missing credentials, or no matches do not fail core nonprofit verification.

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

- `enrichment_mock_enabled`
- `enrichment_candid_enabled`
- `enrichment_candid_endpoint`
- `enrichment_candid_api_key`
- `enrichment_timeout_seconds`
- `enrichment_state_registry_enabled`
- `enrichment_state_registry_mock_enabled`

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

## Peer Benchmarking (Phase 5B)

Model version `2.0.0` adds optional peer-group benchmarking for fairer interpretation of selected metrics.

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

Local dev note:

- keep `api_auth_enabled=false` for unrestricted local testing, or provide `api_key_records_json` with hashed secrets for auth-enabled testing.
- key generation contract (one-time secret display + hashed-at-rest record) is available via `charity_status.auth.build_api_key_record`.

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
  - `status` (`matched`, `unavailable`, `error`, etc.)
  - `normalized_data`
  - `attribution` (`record_id`, `licensed`, `notes`)
  - `freshness.retrieved_at`
  - `error` (when provider had an error)
- `failures[]` (provider-level failures from enrichment run)

### `GET /nonprofits/{ein}/sources/{source_name}`

Returns one normalized source entry for the EIN.

- `404` when source is unsupported/not present for that EIN
- `200` with `source` payload when available

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
