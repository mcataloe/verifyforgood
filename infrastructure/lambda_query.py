"""Compatibility shim for the backend-owned API runtime."""

from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
BACKEND_API_SRC = ROOT / "backend" / "api" / "src"
BACKEND_SHARED_SRC = ROOT / "backend" / "shared" / "src"
PRIVATE_PLATFORM_SRC = ROOT / "private-platform" / "src"

for path in (BACKEND_API_SRC, BACKEND_SHARED_SRC, PRIVATE_PLATFORM_SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


from verification_backend.api import runtime as _runtime  # noqa: E402


_runtime.__name__ = __name__
_runtime.__package__ = __package__
sys.modules[__name__] = _runtime


