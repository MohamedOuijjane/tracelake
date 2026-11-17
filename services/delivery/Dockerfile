FROM python:3.12.8-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY requirements.txt .
# opentelemetry-bootstrap installs instrumentations for the libraries found (fastapi, logging).
RUN pip install -r requirements.txt && opentelemetry-bootstrap -a install

COPY app ./app
RUN useradd --system --uid 10001 app
USER app

EXPOSE 8000
# Auto-instrumentation is configured only through OTEL_* env vars.
CMD ["opentelemetry-instrument", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
