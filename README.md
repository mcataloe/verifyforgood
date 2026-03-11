# Charity Status API

Charity Status API ingests IRS Exempt Organizations data and Form 990 XML-derived datasets into AWS, then serves nonprofit verification and scoring via Lambda + API Gateway.

## Current Architecture

- Runtime: Python 3.11
- Infrastructure: Terraform
- Compute: AWS Lambda
- API: API Gateway (`GET /nonprofit/{ein}`, `POST /verify`, `GET /nonprofit/{ein}/filings`)
- Data lake: S3 + Glue Catalog + Athena
- Serving cache: DynamoDB materialized nonprofit profiles (lazy read-through)

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

Framework location:

- `infrastructure/charity_status/enrichments/base.py`
- `infrastructure/charity_status/enrichments/registry.py`
- `infrastructure/charity_status/enrichments/service.py`
- `infrastructure/charity_status/enrichments/providers/`

Included providers:

- `mock_provider`: deterministic test provider
- `candid`: scaffolded provider module with safe fallback behavior

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

Configuration (Terraform variables):

- `enrichment_mock_enabled`
- `enrichment_candid_enabled`
- `enrichment_candid_endpoint`
- `enrichment_candid_api_key`
- `enrichment_timeout_seconds`

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

### `GET /nonprofit/{ein}`

Returns normalized organization + verification + scores + model + score explanation.
When 990 data exists, includes enriched scoring factors and optional `filing_summary`.

### `POST /verify`

Request body:

```json
{
  "ein": "12-3456789",
  "name": "Optional nonprofit name"
}
```

Performs the same verification workflow as GET and includes conservative name-match metadata.

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
