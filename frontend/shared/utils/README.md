# Shared Utils Package

This package holds tiny pure helpers that stay safe to reuse across frontend surfaces.

Helpers here should remain deterministic and free of app-specific routing, auth, or API assumptions.

Current shared helpers include:

- frontend surface label formatting
- canonical frontend role checks such as `hasRole(...)`, `hasAnyRole(...)`, and `hasAllRoles(...)`

If a helper starts depending on API routes, runtime config, or page-specific state, it belongs elsewhere.
