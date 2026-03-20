# Test Structure Guidance

The repository is still in a compatibility-first migration phase, so tests currently live in more than one conceptual layer even though most files still sit under the root `tests/` directory.

## Current practical split

- `public-core/tests/`
  - target home for pure public-core unit tests
- `private-platform/tests/`
  - target home for private-platform unit and scaffolding tests
- `tests/`
  - current integration and compatibility coverage plus legacy monorepo tests

## How to place new tests

- put deterministic, infrastructure-agnostic tests near `public-core/` when the code under test already lives there
- put private service-area and runtime-boundary tests near `private-platform/` when they only need private-platform package imports
- keep root `tests/` for:
  - end-to-end handler tests
  - compatibility-shim coverage
  - deployment- and packaging-oriented checks
  - mixed-surface tests that still depend on `infrastructure/`

## Compatibility rule

- do not remove root-level compatibility coverage until the live handler imports and deployment wiring no longer depend on the current `infrastructure/` paths
