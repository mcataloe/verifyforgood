# Shared Config Package

This package normalizes the small amount of runtime config that both frontend apps are expected to share.

Current scope:

- API base URL normalization
- API version normalization
- frontend environment normalization from Vite env input

What stays out:

- app-specific feature flags
- route-level config
- portal-only entitlement or billing settings
- marketing-only campaign or content configuration
