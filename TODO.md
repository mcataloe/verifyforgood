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
