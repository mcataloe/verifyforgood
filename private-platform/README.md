# Private Platform (Scaffold)

This directory marks the future destination for proprietary platform integrations.

Current platform/runtime code still exists in this monorepo:

- `infrastructure/lambda_query.py`
- `infrastructure/lambda_refresh.py`
- `infrastructure/lambda_ingest.py`
- `infrastructure/lambda_form990.py`
- `infrastructure/charity_status/platform/`

Target package root after extraction:

- `private-platform/src/charity_status_platform/`

Future private repo responsibilities:

- runtime auth integration
- quota/metering implementation
- proprietary adapters and platform orchestration
- customer/account-specific deployment logic
- all billing and subscription workflow logic
- control-plane and operator workflow orchestration
- Lambda entrypoints and transport response shaping
