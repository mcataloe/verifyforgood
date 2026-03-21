from legacy_namespace import LEGACY_TOP_LEVEL_MODULES, bootstrap_legacy_namespace


globals().update(bootstrap_legacy_namespace(__name__))

__all__ = tuple(sorted(set(LEGACY_TOP_LEVEL_MODULES) | {name for name in globals() if not name.startswith("_")}))
