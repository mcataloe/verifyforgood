# Admin Operations

Purpose:

- private operator and internal administration boundary
- home for run tracking, admin workflow support, and future operational tooling behind admin-only interfaces

Allowed contents:

- ops run stores and workflow state
- admin-only workflow services
- internal operational reporting and support helpers

Forbidden contents:

- public-core deterministic evaluation logic
- customer-facing public package APIs

Dependency direction:

- may depend on `charity_status`
- may depend on customer account and billing/usage services
