# Portal Identity, Organization Onboarding, and Membership Status

## Status

team management UX hardened

## Next Phase

22D

## Scope

- Identity domain modeling
- DynamoDB schema
- Service layer contracts

## Deployment Notes

- The identity table schema now includes the `api_key_lookup` GSI for organization-managed API key resolution.
- On existing tables, DynamoDB creates new GSIs asynchronously; Terraform rollouts should wait for the index to reach `ACTIVE` before treating an interrupted apply as failed.
