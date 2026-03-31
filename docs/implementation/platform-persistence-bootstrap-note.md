# Platform Persistence Bootstrap Note

## Intent

Follow-on persistence work should add PostgreSQL support without changing
service-call sites or route contracts.

## Bootstrap Rules

- choose persistence implementation by domain, not with one global datastore
  switch
- keep existing repository and store protocols as the primary seam
- allow temporary mixed mode
  - DynamoDB for not-yet-migrated domains
  - PostgreSQL for migrated domains
- keep current DynamoDB env vars during the transition
- add PostgreSQL config additively

## Expected Runtime Config Additions

- PostgreSQL connection string or equivalent host/user/password/db settings
- per-domain persistence selection flags
- secret-backed credentials for Lambda/runtime use

## First Domains to Wire Through the Bootstrap

1. portal identity and customer accounts
2. organization settings
3. control-plane and billing

## Non-Goals

- no route-contract changes
- no frontend payload changes
- no migration of Athena/S3 nonprofit and filing datasets in the initial pivot
