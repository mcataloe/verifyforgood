# Runtime

Purpose:

- private runtime composition boundary
- home for environment-driven adapter assembly, handler composition, and future internal entrypoint orchestration

Allowed contents:

- runtime config objects
- adapter builders and runtime composition helpers
- handler-side service assembly
- future private entrypoints and portal backend composition code

Forbidden contents:

- public-core deterministic domain logic
- raw Terraform/deploy artifacts

Dependency direction:

- may depend on `charity_status`
- may depend on other `charity_status_platform` service areas
- deploy-time code may invoke this layer, not the reverse
