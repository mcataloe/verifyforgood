"""Local entrypoint for the backend API runtime."""

from __future__ import annotations

from charity_status_backend.shared.local_dev import load_backend_local_env
import uvicorn


def main() -> None:
    load_backend_local_env()
    uvicorn.run("charity_status_backend.api.app:app", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
