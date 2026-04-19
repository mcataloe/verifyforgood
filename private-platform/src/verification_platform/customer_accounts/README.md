# Customer Accounts

Purpose:

- private account, tenant, and organization-provisioning boundary
- home for control-plane account lifecycle, managed credentials, organization settings, and future customer-portal backend services

Allowed contents:

- account and workspace lifecycle services
- organization provisioning and settings
- managed API key and OAuth client administration
- customer/account audit records and provisioning workflows

Forbidden contents:

- public-core deterministic domain logic
- deploy-only infrastructure configuration

Dependency direction:

- may depend on `verification`
- billing/usage services may consume account services
- public-core must not depend on this package

