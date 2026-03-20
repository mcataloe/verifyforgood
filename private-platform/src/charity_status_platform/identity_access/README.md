# Identity Access

Purpose:

- private authentication, authorization, and credential-management boundary
- home for API key auth, admin auth, OAuth client credentials, auth context providers, and access-policy orchestration

Allowed contents:

- auth principals and credential records
- auth flows and key/token issuance helpers
- auth context providers and request identity extraction
- access policy enforcement that is specific to private platform behavior

Forbidden contents:

- public-core deterministic nonprofit evaluation logic
- Terraform or deploy-time wiring

Dependency direction:

- may depend on `charity_status`
- must not be imported by public-core packages
