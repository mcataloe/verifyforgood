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
