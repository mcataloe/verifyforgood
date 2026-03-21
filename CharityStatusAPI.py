import importlib
import sys
import warnings


_compat = importlib.import_module("charitystatusapi")
warnings.warn(
    "CharityStatusAPI is a compatibility namespace. Prefer verification_platform.* or charity_status.* imports for new code.",
    DeprecationWarning,
    stacklevel=2,
)

for module_name, module in list(sys.modules.items()):
    if module_name == "charitystatusapi" or module_name.startswith("charitystatusapi."):
        sys.modules[module_name.replace("charitystatusapi", __name__, 1)] = module

globals().update(_compat.__dict__)
__all__ = getattr(_compat, "__all__", ())
__path__ = getattr(_compat, "__path__", [])
