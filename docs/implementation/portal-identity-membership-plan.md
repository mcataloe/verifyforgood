# Portal Identity, Organization Onboarding, and Membership Plan

## Summary

This plan defines the next implementation slice for portal identity, organization onboarding, and membership management. The work should align to the existing private-platform boundaries:

- `private-platform/src/charity_status_platform/identity_access/` for authentication, authorization, and request identity concerns
- `private-platform/src/charity_status_platform/customer_accounts/` for organization provisioning, onboarding, and account lifecycle concerns

The initial implementation should preserve compatibility boundaries and keep service logic separate from datastore-specific adapters.

## Upcoming Scope

### User Authentication

- Establish durable user identity records for portal access.
- Support authentication flows that can evolve from current placeholder portal behavior to real identity providers.
- Keep authentication orchestration in the identity-access boundary rather than coupling it to customer-account provisioning logic.

### Organization Creation

- Introduce organization onboarding flows for creating a managed customer organization record.
- Keep organization creation behavior in customer-account services with explicit repository interfaces.
- Preserve compatibility with existing organization settings and portal organization context patterns where possible.

### Membership Relationships

- Model the relationship between users and organizations through membership records rather than embedding access directly on user entities.
- Support membership-aware account context for future portal and backend authorization decisions.
- Keep membership rules expressed in service contracts, not in DynamoDB-specific condition logic.

### Invitation Flow

- Add invitation records and invitation acceptance flows for organization membership onboarding.
- Separate invitation lifecycle behavior from authentication details so invited users can be attached to future identity-provider flows.
- Keep invitation state transitions explicit and testable.

### Frontend Integration

- Replace placeholder portal identity assumptions with backend-driven user, organization, and membership context over time.
- Align frontend session and organization context loading with stable backend contracts.
- Preserve incremental rollout so portal slices can adopt real identity and membership behavior without broad UI churn.

## DynamoDB Single-Table Identity Structure

### Intent

Use a single DynamoDB table for the early identity domain while keeping repository and service interfaces datastore-agnostic.

### Conceptual Entities

- user
- organization
- membership
- invitation

### Initial Access Pattern Direction

- Store each conceptual entity as its own typed record.
- Use composite keys that group records by primary aggregate and support common onboarding and membership lookups.
- Add secondary access patterns only for concrete service needs such as lookup by email, organization membership listing, or invitation token resolution.

### Boundary Rules

- Domain services should operate on normalized user, organization, membership, and invitation models.
- Repository interfaces should expose capability-oriented methods such as create user, create organization, add membership, and resolve invitation.
- DynamoDB-specific key layout, entity prefixes, and index usage should remain inside repository adapter implementations.

### Migration Readiness

- Keep the conceptual model relational even if the initial table design is denormalized.
- Avoid encoding business rules directly into item-shape assumptions that would complicate a later move to PostgreSQL or Aurora Serverless.
