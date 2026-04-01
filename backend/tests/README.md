# Backend Test Guidance

This directory is the future home for backend package-local tests.

Use `backend/tests/` for:

- runtime bootstrap tests that target `charity_status_backend.*`
- local entrypoint tests once live runtime logic moves out of `infrastructure/`
- backend-only packaging and process-boundary tests that do not belong in `public-core/tests/` or `private-platform/tests/`

For the current compatibility-first phase:

- keep root `tests/` as the source of truth for backend scaffolding and packaging checks
- keep live handler behavior coverage under root `tests/` while deployed imports still resolve through `infrastructure/`
