# TODO

## TODO-ARCH-001

### Title

Evaluate migration of identity domain from DynamoDB to PostgreSQL/Aurora Serverless once customer growth or reporting complexity justifies relational storage.

### Rationale

The identity domain includes relational structures:

- users
- organizations
- memberships
- invitations

DynamoDB is being used initially for cost control.

### Migration Triggers

- SSO rollout
- enterprise onboarding requirements
- complex reporting needs
- audit requirements
- 50+ paying customers

### Constraint

Service and repository interfaces should remain datastore-agnostic.

## TODO-ARCH-002

### Title

Reconcile API Endpoints

### Rationale

Need to ensure that all API endpoints that are expected by the frontend repo are deployed in the infrastructure / data access layer.

### Migration Triggers

None

### Constraint

None

## TODO-ARCH-003

### Title

Link portal organizations to control-plane accounts and subscriptions for org-managed API keys.

### Rationale

Phase 19L introduces organization-managed API keys in the identity domain. Until portal organizations provision or map to control-plane accounts, these keys use a temporary compatibility model:

- `account_id = organization_id`
- `workspace_id = organization_id`
- `plan_id = free`

That is enough for initial authentication, but it does not inherit real billing, subscription, or entitlement state.

### Migration Triggers

- portal billing parity
- organization subscription-aware entitlements
- API key plan inheritance requirements
- multi-org account mapping

### Constraint

Keep the org-managed API-key repository/service interfaces stable so real control-plane linkage can replace the temporary compatibility mapping without changing frontend or handler contracts.

## TODO-ARCH-004

### Title

Reconcile portal subscription scaffolding with control-plane billing accounts and subscriptions.

### Rationale

Phase 19M introduces `PLAN` and `SUBSCRIPTION` entities in the portal identity domain so organization-linked subscription state can exist before full billing parity. The repo already has a mature control-plane billing model, so these portal records are scaffolding until a real linkage model is implemented.

### Migration Triggers

- portal billing UI parity
- Stripe-backed portal subscription changes
- entitlement inheritance from paid subscriptions
- organization to control-plane account mapping

### Constraint

Keep the portal `PlanRepository`, `SubscriptionRepository`, and `SubscriptionService` contracts stable so control-plane linkage can replace the scaffolded storage model without changing portal-facing callers.

## TODO-ARCH-005

### Title

SSO integration design details pending.

### Rationale

Phase 19P adds identity-provider seams and user provider metadata, but it does not define the full SAML/OIDC integration model yet.

Open design areas include:

- provider configuration storage
- tenant-to-provider mapping
- account linking and JIT provisioning rules
- assertion validation boundaries
- admin onboarding and certificate/metadata rotation

### Migration Triggers

- first SAML pilot
- first OIDC enterprise integration
- provider discovery and login initiation requirements

### Constraint

Keep the `IdentityProviderService` abstraction and user provider fields stable so future SSO support can plug in without breaking the existing local-password auth flow.

## TODO-ARCH-006

### Title

Define tenant-resolution support for non-portal machine clients on nonprofit query routes.

### Rationale

Phase 20A makes nonprofit query routes organization-aware and intentionally supports only:

- organization-managed API keys
- portal bearer sessions with current-organization headers

Generic control-plane API keys and OAuth client-credentials tokens remain unsupported until there is a stable way to resolve them to an organization membership or equivalent tenant scope.

### Migration Triggers

- tenant-scoped machine-to-machine access requirements
- partner or integration clients that need nonprofit query access
- organization-linked OAuth client design

### Constraint

Keep the new tenant nonprofit service contract stable so future non-portal machine-auth support can plug in by adding tenant resolution, not by changing nonprofit lookup callers.

## TODO-ARCH-007

### Title

Decide whether nonprofit source, compliance, and federal-awards routes need dedicated organization usage metrics.

### Rationale

Phase 20B adds dedicated usage counters for:

- nonprofit lookup requests
- nonprofit search requests
- nonprofit filing lookup requests

Other tenant-scoped nonprofit read routes still rely on broader request metering and do not yet have dedicated per-route usage categories.

### Migration Triggers

- subscription packaging for source/compliance data
- per-feature usage reporting requirements
- differentiated billing for supplemental nonprofit data routes

### Constraint

Preserve the Phase 20B metric names and route-to-metric mapping for lookup, search, and filings so any future expansion is additive.

## TODO-ARCH-008

### Title

Move premium enrichment gating to a registry-driven feature map for future paid providers.

### Rationale

Phase 20C enforces feature flags for current premium integrations through the existing feature-to-integration mapping. As new paid enrichment providers are added, manually extending per-feature mappings in query orchestration will become harder to maintain.

### Migration Triggers

- onboarding additional premium enrichment providers
- plan-tier specific source packaging
- self-serve premium integration rollout

### Constraint

Keep the Phase 20C nonprofit-service enforcement seam stable so future premium integrations can plug in by extending registry metadata and flag mappings instead of changing nonprofit route contracts.

## TODO-ARCH-009

### Title

Evaluate migrating billing and organization-settings routes onto the centralized tenant authorization middleware.

### Rationale

Phase 20D centralizes tenant authorization for nonprofit, membership, and organization API-key routes. Billing and settings endpoints still need a final decision on how portal organizations, account linkage, and tenant scope should align before they fully share the same middleware contract.

### Migration Triggers

- portal and billing account linkage finalized
- organization settings expanded beyond nonprofit integrations
- need for one consistent org-scope authorization model across all portal routes

### Constraint

Keep the Phase 20D `TenantContext` contract stable so additional organization-scoped routes can adopt the middleware without changing existing nonprofit, membership, or API-key handler contracts.

## TODO-ARCH-010

### Title

Replace the customer-user address-search placeholder with a backend-supported nonprofit discovery workflow.

### Rationale

Phase 20E moves the real tenant-aware nonprofit experience onto the portal workspace route using the backend-supported EIN and name search endpoints. The older customer-user address-search placeholder remains out of scope until the platform exposes a real address or richer organization discovery API.

### Migration Triggers

- backend address-search support for nonprofit discovery
- customer-user IA refresh for search and review workflows
- need to retire placeholder local datasets from the portal surface

### Constraint

Keep the Phase 20E workspace nonprofit-search contract stable so future address or expanded discovery support can plug into the existing portal organization provider and API client without changing tenant header behavior.

## TODO-ARCH-011

### Title

Define a stable export and warehouse shape for nonprofit access audit analytics.

### Rationale

Phase 20F adds structured audit logging for tenant-aware nonprofit reads and stores analytics-oriented fields inside the audit metadata blob. That is sufficient for in-product auditing and incremental reporting, but downstream export and warehouse consumers may eventually need a stricter schema for durable analytics.

### Migration Triggers

- audit log export to a data warehouse or lake
- BI dashboards built on nonprofit access activity
- compliance or customer reporting that depends on stable audit dimensions

### Constraint

Keep the Phase 20F nonprofit audit event taxonomy stable and additive so future export shaping can standardize metadata without breaking existing audit records.

## TODO-ARCH-012

### Title

Decide whether public Stripe pricing should default to tax-inclusive or tax-exclusive presentation.

### Rationale

Phase 21A establishes Stripe as the provisional billing provider, but the customer-facing pricing model still needs a durable default. Tax presentation affects checkout clarity, invoice expectations, and how the product markets plan pricing across regions.

### Migration Triggers

- Stripe Tax rollout
- public pricing page refresh
- multi-region billing launch

### Constraint

Keep the organization-scoped billing model and backend billing abstractions stable so tax presentation can be finalized without changing the Phase 21 subscription service boundaries.

## TODO-ARCH-013

### Title

Confirm downgrade semantics for paid subscriptions: immediate restriction or next-cycle effective change.

### Rationale

Stripe-backed plan changes need a durable downgrade policy so entitlement enforcement, billing communication, and webhook-driven synchronization remain consistent. Customer expectations and support workflows will differ depending on whether access changes immediately or at the next renewal boundary.

### Migration Triggers

- paid plan downgrade implementation
- billing policy publication
- support and retention workflow definition

### Constraint

Preserve the Phase 21 organization-scoped subscription model and local pending-plan fields so the final downgrade policy can be applied without changing the core billing abstractions.

## TODO-ARCH-014

### Title

Confirm whether the free tier stays Stripe-less or every organization receives a Stripe customer object.

### Rationale

Phase 21A keeps free-tier billing behavior open. The choice affects onboarding flow complexity, reconciliation expectations, billing data completeness, and when Stripe becomes part of the lifecycle for organizations that never upgrade.

### Migration Triggers

- free-to-paid conversion funnel optimization
- invoice and tax requirements for all organizations
- desire for uniform billing identity across tiers

### Constraint

Keep `organization_id` as the canonical billing scope and treat Stripe identifiers as attached billing state so free-tier onboarding policy can change without redefining organization billing identity.
