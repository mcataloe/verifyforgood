# Runtime

Purpose:

- private runtime composition boundary
- home for environment-driven adapter assembly, handler composition, and future internal entrypoint orchestration

Allowed contents:

- runtime config objects
- adapter builders and runtime composition helpers
- handler-side service assembly
- future private entrypoints and portal backend composition code
- shared backend transport contract compatibility exports
- canonical mapping of live backend entrypoints during the transition period

Forbidden contents:

- public-core deterministic domain logic
- raw Terraform/deploy artifacts

Dependency direction:

- may depend on `charity_status`
- may depend on other `charity_status_platform` service areas
- deploy-time code may invoke this layer, not the reverse

Current transition helpers:

- `backend_contracts.py`
  - canonical private-platform import root for API response-envelope and route-version helpers that still live under `charity_status.api`
- `entrypoints.py`
  - machine-readable map of the current live backend entrypoints in `infrastructure/lambda_*.py`
  - keeps the future private-platform ownership visible without forcing a handler move yet
