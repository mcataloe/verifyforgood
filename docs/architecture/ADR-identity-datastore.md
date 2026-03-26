# Identity Datastore Selection

## Status

provisional

## Decision

Use DynamoDB for the identity domain during early development.

## Context

- Cost minimization is a priority during the early stage.
- The platform should remain serverless initially where practical.
- The identity domain is relational in nature and may migrate later as product needs mature.

## Consequences

- A repository abstraction layer is required between domain services and persistence.
- Business logic should not couple directly to DynamoDB item shapes or access patterns.
- The conceptual domain model should remain normalized even if the physical storage model is denormalized.
