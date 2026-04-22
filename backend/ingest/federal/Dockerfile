FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FORM990_WORKSPACE_DIR=/tmp/charity-status/form990
ENV FORM990_WORKSPACE_MAX_BYTES=34359738368
ENV PYTHONPATH=/app:/app/backend/ingest/federal/src:/app/backend/shared/src

WORKDIR /app

COPY infrastructure/requirements.txt /app/infrastructure/requirements.txt

RUN python -m pip install --no-cache-dir --upgrade pip && \
    python -m pip install --no-cache-dir -r /app/infrastructure/requirements.txt

COPY backend/ingest/federal/src /app/backend/ingest/federal/src
COPY backend/shared/src /app/backend/shared/src

ENTRYPOINT ["python", "-m", "verification.backend.ingest.federal.cli"]
CMD ["monthly-worker"]

