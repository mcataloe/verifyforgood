"""Local entrypoint for the backend platform API runtime."""

from __future__ import annotations

import asyncio
import os

from verification.backend.shared.local_dev import load_backend_local_env
import uvicorn


def _env_port() -> int:
    raw = str(
        os.environ.get("PLATFORM_API_PORT")
        or os.environ.get("PORT")
        or "8000"
    ).strip()
    return int(raw)


def main() -> None:
    load_backend_local_env()
    uvicorn.run(
        "verification.backend.platform.api.app:app",
        host=str(os.environ.get("PLATFORM_API_HOST") or "0.0.0.0").strip() or "0.0.0.0",
        port=_env_port(),
        loop=asyncio.new_event_loop,
        http="h11",
    )


if __name__ == "__main__":
    main()
