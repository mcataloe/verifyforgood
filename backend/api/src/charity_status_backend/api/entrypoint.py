"""Local entrypoint for the backend API runtime."""

from __future__ import annotations

import uvicorn


def main() -> None:
    uvicorn.run("charity_status_backend.api.app:app", host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()

