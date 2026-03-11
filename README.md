# Charity Status API

Charity Status API ingests IRS Exempt Organizations data and Form 990 XML-derived datasets into AWS, then serves nonprofit verification and scoring via Lambda + API Gateway.

## Current Architecture

- Runtime: Python 3.11
- Infrastructure: Terraform
- Compute: AWS Lambda
- API: API Gateway (`GET /nonprofit/{ein}`, `POST /verify`, `GET /nonprofit/{ein}/filings`)
- Data lake: S3 + Glue Catalog + Athena

## AWS Data Flow

1. `lambda_ingest.py` downloads IRS EO CSV files (`eo1.csv`-`eo4.csv`) into S3.
2. `lambda_form990.py` ingests Form 990 index/XML and writes normalized JSONL datasets.
3. Glue catalogs EO/BMF and Form 990 normalized datasets.
4. `lambda_query.py` handles verification/scoring endpoints using Athena-backed data.

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
