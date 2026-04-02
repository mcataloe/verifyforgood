FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app:/app/infrastructure:/app/private-platform/src:/app/backend/ingest-task/src:/app/backend/shared/src

WORKDIR /app

COPY infrastructure/requirements.txt /app/infrastructure/requirements.txt

RUN python -m pip install --no-cache-dir --upgrade pip && \
    python -m pip install --no-cache-dir -r /app/infrastructure/requirements.txt

COPY infrastructure /app/infrastructure
COPY private-platform/src /app/private-platform/src
COPY backend/ingest-task/src /app/backend/ingest-task/src
COPY backend/shared/src /app/backend/shared/src

ENTRYPOINT ["python", "-m", "charity_status_backend.ingest_task.cli"]
CMD ["monthly-worker"]
