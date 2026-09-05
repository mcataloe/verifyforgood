FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.6 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV PYTHONPATH=/app:/app/backend/customer-api/src:/app/backend/platform-api/src:/app/backend/shared/src:/app/backend/ingest/federal/src:/app/backend/ingest/state/src:/app/backend/ingest/shared/src

WORKDIR /app/backend

COPY backend/pyproject.toml backend/uv.lock /app/backend/

RUN uv sync --locked --no-dev --no-cache

COPY backend/customer-api/src /app/backend/customer-api/src
COPY backend/platform-api/src /app/backend/platform-api/src
COPY backend/shared/src /app/backend/shared/src
COPY backend/ingest/federal/src /app/backend/ingest/federal/src
COPY backend/ingest/state/src /app/backend/ingest/state/src
COPY backend/ingest/shared/src /app/backend/ingest/shared/src

EXPOSE 8000

CMD ["/app/backend/.venv/bin/uvicorn", "verification.backend.platform.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
