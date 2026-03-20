# Infrastructure Deployment (Scaffold)

This directory marks the future deployment-artifacts repository boundary.

Current deployment assets remain under:

- `infrastructure/*.tf`
- `infrastructure/*.tfvars`
- `infrastructure/backend-*.hcl`
- Lambda packaging scripts and zip outputs

Current in-repo boundary note:

- `infrastructure/README.md` now documents the short-term dual role of `infrastructure/` and its long-term deployment-only direction

Target deployment-oriented structure after migration:

- `infrastructure/terraform/`
- `infrastructure/env/`
- `infrastructure/scripts/`
- `infrastructure/lambda_shims/`

Future extracted repo should contain:

- Terraform modules/environments
- CI/CD deploy pipelines
- environment-specific config and secrets handling
- packaging and deployment shims only

Boundary rule:

- deployment artifacts belong here
- business logic does not
