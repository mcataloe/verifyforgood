"""Private-platform package root.

This package defines the internal service-area boundaries for proprietary
platform logic while preserving compatibility with the current monorepo paths.
"""

from pkgutil import extend_path

__path__ = extend_path(__path__, __name__)

from .legacy import (
    LEGACY_MODULE_ALIASES,
    LEGACY_NAMESPACE_ROOT,
    capability_module_names,
    legacy_module_aliases,
    resolve_legacy_module_path,
)

__all__ = [
    "LEGACY_MODULE_ALIASES",
    "LEGACY_NAMESPACE_ROOT",
    "identity_access",
    "customer_accounts",
    "nonprofits",
    "billing_usage",
    "admin_operations",
    "runtime",
    "notifications",
    "capability_module_names",
    "legacy_module_aliases",
    "resolve_legacy_module_path",
]
