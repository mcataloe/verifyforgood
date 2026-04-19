FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app:/app/backend/worker/src:/app/backend/shared/src

WORKDIR /app

COPY infrastructure/requirements.txt /app/infrastructure/requirements.txt

RUN python -m pip install --no-cache-dir --upgrade pip && \
    python -m pip install --no-cache-dir -r /app/infrastructure/requirements.txt

COPY backend/worker/src /app/backend/worker/src
COPY backend/shared/src /app/backend/shared/src

CMD ["python", "-m", "verification_backend.worker.entrypoint"]

