# Private-Platform Tests

Purpose:

- future home for unit tests that target `private-platform/src/verification_platform/` boundaries directly

What belongs here:

- unit tests for private service areas such as identity/access, customer accounts, billing/usage, admin operations, runtime, and notifications
- compatibility tests for private-platform re-export modules and runtime maps

What does not belong here:

- Terraform/deployment validation
- public-core deterministic unit tests
- full end-to-end API behavior tests that still need the current runtime entrypoints

Current note:

- root-level `tests/` remains the live integration and compatibility test surface while handler imports still point at `infrastructure/`

