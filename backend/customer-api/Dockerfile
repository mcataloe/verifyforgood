FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app:/app/backend/customer-api/src:/app/backend/shared/src

WORKDIR /app

COPY infrastructure/requirements.txt /app/infrastructure/requirements.txt
COPY infrastructure/requirements-api.txt /app/infrastructure/requirements-api.txt

RUN python -m pip install --no-cache-dir --upgrade pip && \
    python -m pip install --no-cache-dir -r /app/infrastructure/requirements-api.txt

COPY backend/customer-api/src /app/backend/customer-api/src
COPY backend/shared/src /app/backend/shared/src

EXPOSE 8000

CMD ["uvicorn", "verification.backend.customer.api.app:app", "--host", "0.0.0.0", "--port", "8000"]

