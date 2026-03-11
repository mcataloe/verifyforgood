# Charity Status API

Charity Status API ingests IRS Exempt Organizations (EO/BMF-style) data into AWS and exposes a Lambda-backed API for nonprofit EIN verification.

## Current Architecture

- Runtime: Python 3.11
- Infrastructure: Terraform
- Compute: AWS Lambda
- API: API Gateway (`GET /nonprofit/{ein}`, `POST /verify`)
- Data lake: S3 + Glue Catalog + Athena

## AWS Data Flow

1. `lambda_ingest.py` triggers concurrent download of IRS EO CSV files (`eo1.csv`-`eo4.csv`).
2. Raw EO files are uploaded to S3 under `s3://<BUCKET>/<PREFIX>/` (default prefix `eo_bmf/`).
3. Glue Catalog table metadata points Athena at that S3 CSV location.
4. `lambda_query.py` receives API Gateway requests.
5. Query Lambda validates EIN, queries Athena, maps the row into a domain response, and calculates conservative v1 scores.

## Ingest Architecture (Phase 2)

- Thin handler: `infrastructure/lambda_ingest.py`
- Reusable ingest modules: `infrastructure/charity_status/ingest/`
  - `irs_files.py`: EO source list and bucket/prefix key helpers
  - `downloader.py`: async download adapter
  - `uploader.py`: S3 upload abstraction
  - `result.py`: structured ingest result payload builder
  - `interfaces.py`: extension interfaces/types for future ingest providers

Current ingest output includes:

- `status`
- `downloaded` / `failed` (backward-compatible lists)
- `downloaded_count` / `failed_count`
- `started_at`, `completed_at`, `duration_ms`
- `files` (per-file status and error details)

## Form 990 Foundation (Phase 4A)

Phase 4A adds foundational Form 990 ingestion plumbing without changing the platform architecture.

New modules live under `infrastructure/charity_status/form990/`:

- `index.py`: index/metadata record parsing
- `ingest.py`: ingestion orchestration and status manifest generation
- `storage.py`: S3 key strategy and JSONL serialization helpers
- `parser.py`: XML parse wrapper with safe error typing
- `resolver.py`: version-aware, multi-selector field resolution
- `extractors/metadata.py`: canonical metadata extraction only

Raw vs normalized separation:

- Raw 990 XML references/content: `s3://<BUCKET>/<FORM990_RAW_PREFIX>/...`
- Normalized metadata JSONL: `s3://<BUCKET>/<FORM990_METADATA_PREFIX>/...`
- Parse manifests/status: `s3://<BUCKET>/<FORM990_MANIFEST_PREFIX>/...`
- Future derived metrics and scoring are intentionally separate and not implemented in Phase 4A.

## API Endpoints

### `GET /nonprofit/{ein}`

Path parameter:

- `ein`: EIN in forms like `12-3456789`, `123456789`, or with spaces.

Behavior:

- Invalid EIN -> `400`
- EIN not found -> `404`
- Success -> `200` with normalized payload:
  - `organization`
  - `verification`
  - `scores`
  - `model`
  - optional `source_record`
  - `score_explanation`
  - `name_verification`

### `POST /verify`

Request body:

```json
{
  "ein": "12-3456789",
  "name": "Optional nonprofit name"
}
```

Behavior:

- Normalizes EIN and performs the same Athena-backed verification workflow as GET.
- If `name` is provided, includes conservative name comparison fields:
  - `provided_name`
  - `irs_name`
  - `name_match`
  - `match_confidence`

Example response excerpt:

```json
{
  "organization": {
    "name": "Helping Hands Inc.",
    "ein": "12-3456789"
  },
  "scores": {
    "overall": 82,
    "trust": 84,
    "financial_resilience": null,
    "transparency": 61,
    "compliance": 92
  },
  "score_explanation": {
    "model_version": "1.0.0",
    "confidence": "medium",
    "factors": {
      "ein_valid": true,
      "record_found": true,
      "status_present": true,
      "deductibility_present": true,
      "ntee_present": true,
      "tax_period_present": true,
      "financial_fields_present": false,
      "name_match": true
    },
    "notes": [
      "Score is based on EO/BMF-style IRS data only",
      "Full 990-based financial and governance scoring not yet implemented"
    ]
  }
}
```

## Current Scope vs Planned

Implemented now:

Query mapping and scoring are currently based only on EO/BMF-style IRS fields available in Athena.
- v1 scores do **not** represent full 990 financial analysis.
- Unsupported fields are returned as `null` instead of inferred values.
- EO ingest currently covers IRS EO CSV source files (`eo1.csv`-`eo4.csv`) only.

Planned later:

- Form 990 metadata ingestion hooks (`infrastructure/charity_status/future/form990.py`)
- External enrichment provider hooks (`infrastructure/charity_status/future/enrichments.py`)
- 990 financial and governance extraction from XML schedules
- 990-driven scoring enhancements built on normalized derived datasets

Current 990 limitation:

- Phase 4A extracts metadata fields only (`ein`, tax period/year, filing metadata, return type, source references, parse status).
- Full financial/governance extraction is not implemented yet.

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

- Query Lambda package is created from the `infrastructure/` directory so shared query modules are deployed with `lambda_query.py`.
- Ingest Lambda packaging remains unchanged.
