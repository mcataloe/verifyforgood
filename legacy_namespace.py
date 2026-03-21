from __future__ import annotations

import importlib
import sys
import warnings


TARGET_NAMESPACE_ROOT = "charity_status"
LEGACY_TOP_LEVEL_MODULES: tuple[str, ...] = (
    "api",
    "auth",
    "billing",
    "branding",
    "control_plane",
    "core",
    "decision",
    "enrichments",
    "evidence",
    "form990",
    "future",
    "ingest",
    "models",
    "normalization",
    "ops",
    "platform",
    "policy",
    "query",
    "scoring",
    "serving",
    "sources",
    "state_registry",
)


def bootstrap_legacy_namespace(alias_root: str) -> dict[str, object]:
    warnings.warn(
        f"{alias_root} is a compatibility namespace. Prefer verification_platform.* or charity_status.* imports for new code.",
        DeprecationWarning,
        stacklevel=2,
    )
    target_root = importlib.import_module(TARGET_NAMESPACE_ROOT)
    for module_name in LEGACY_TOP_LEVEL_MODULES:
        sys.modules[f"{alias_root}.{module_name}"] = importlib.import_module(f"{TARGET_NAMESPACE_ROOT}.{module_name}")
    exported: dict[str, object] = {}
    for export_name in getattr(target_root, "__all__", ()):
        try:
            exported[export_name] = getattr(target_root, export_name)
        except AttributeError:
            continue
    return exported


__all__ = [
    "LEGACY_TOP_LEVEL_MODULES",
    "TARGET_NAMESPACE_ROOT",
    "bootstrap_legacy_namespace",
]
