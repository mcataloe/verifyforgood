# Infrastructure Deployment (Scaffold)

This directory marks the future deployment-artifacts repository boundary.

Current deployment assets remain under:

- `infrastructure/*.tf`
- `infrastructure/*.tfvars`
- `infrastructure/backend-*.hcl`
- Lambda packaging scripts and zip outputs

Future extracted repo should contain:

- Terraform modules/environments
- CI/CD deploy pipelines
- environment-specific config and secrets handling
