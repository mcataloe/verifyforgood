"""Future public-core package root.

This package is intentionally minimal during the scaffolding phase.
The canonical implementation still lives under ``infrastructure/verification``.
"""

from pkgutil import extend_path

__path__ = extend_path(__path__, __name__)

try:
    from .models import NonprofitResponse
except ImportError:
    NonprofitResponse = None

__all__: list[str] = []

if NonprofitResponse is not None:
    __all__.append("NonprofitResponse")
