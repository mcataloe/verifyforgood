# Shared Types Package

This package holds app-agnostic frontend types that can be reused across marketing and portal without leaking runtime wiring between them.

Current scope:

- app metadata and surface identifiers
- normalized frontend runtime config types
- backend-aligned API envelope and error contracts
- shared pricing-plan catalog contract types
- canonical frontend access-role vocabulary

Current canonical frontend roles:

- `developer`
- `portal_admin`
- `customer_admin`
- `customer_user`

Anti-pattern:

- do not move endpoint-specific portal view models here just because they are written in TypeScript
