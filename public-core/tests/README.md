# Public-Core Tests

Purpose:

- future home for unit tests that exercise extracted `public-core/src/verification/` modules directly

What belongs here:

- deterministic unit tests for public-core modules
- parser, normalization, schema, and policy tests that do not require deployment/runtime setup

What does not belong here:

- Lambda handler tests
- AWS adapter tests
- private-platform auth, billing, control-plane, or ops tests

Current note:

- the repository still keeps most tests under the root `tests/` directory while the split remains compatibility-first
- new tests for already extracted public-core modules should prefer this area when they do not need the legacy monorepo import paths

