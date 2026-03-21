# Infrastructure Directory Boundary

Current role:

- this directory still contains both deployment assets and active Python runtime code
- Terraform, env files, Lambda entrypoints, and the current `charity_status` implementation all still live here today
- Terraform resource names are centralized in `main.tf` locals and can opt into the standardized `<namespace>-<platform>-<purpose>-<environment>-<region>` pattern without forcing immediate renames of deployed infrastructure

Target role:

- deployment/config/wiring only
- future long-term contents should converge on:
  - `terraform/`
  - `env/`
  - `scripts/`
  - `lambda_shims/`

Allowed contents in the target state:

- Terraform modules and environment configuration
- packaging scripts
- thin deployment-time handler shims when needed for compatibility

Forbidden contents in the target state:

- reusable domain/business logic
- long-lived platform service implementations
- proprietary platform adapters outside temporary compatibility shims

Dependency direction:

- `infrastructure/` may package and deploy runtime entrypoints
- application/domain code must not depend on deployment-only modules from `infrastructure/`

Migration note:

- this boundary is documented now so later refactors can move code out incrementally without breaking current deployment assumptions
- naming is decoupled from product branding so infrastructure identity does not have to change when customer-facing names do
- use `docs/contributor-naming-rules.md` for the short naming rules shared across runtime and infrastructure work
- the current normalization rules, compatibility aliases, and legacy exceptions are documented in `docs/infrastructure-naming-normalization.md`
- the monthly private-ingest architecture and operations docs live in `docs/monthly-ingest-architecture.md` and `docs/monthly-ingest-runbook.md`
