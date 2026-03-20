# Shared API Package

This package contains the smallest shared API foundation justified by the current repo contracts.

Current scope:

- route helpers aligned with the backend `v1` path conventions
- a tiny JSON request helper that expects the standard API envelope
- a typed request error for shared portal/marketing consumers

What stays out for now:

- endpoint-by-endpoint SDK wrappers
- caching/state libraries
- portal-specific billing clients
- marketing-specific form submission clients
