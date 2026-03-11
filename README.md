# Charity Status API

Charity Status API ingests IRS Exempt Organizations (EO/BMF-style) data into AWS and exposes a Lambda-backed API for nonprofit EIN verification.

## Current Architecture

- Runtime: Python 3.11
- Infrastructure: Terraform
- Compute: AWS Lambda
- API: API Gateway (`GET /nonprofit/{ein}`)
- Data lake: S3 + Glue Catalog + Athena

## AWS Data Flow

1. `lambda_ingest.py` downloads IRS source files and uploads them to S3.
2. Glue Catalog table metadata points Athena at the S3 CSV location.
3. `lambda_query.py` receives API Gateway requests.
4. Query Lambda validates EIN, queries Athena, maps the row into a domain response, and calculates conservative v1 scores.

## API Endpoint

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

## Phase 1 Query Model

Query mapping and scoring are currently based only on EO/BMF-style IRS fields available in Athena.

Important limits:

- v1 scores do **not** represent full 990 financial analysis.
- Unsupported fields are returned as `null` instead of inferred values.

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
