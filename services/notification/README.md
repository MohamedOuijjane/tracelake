# notification

Notification service on FastAPI (Python 3.12). It accepts a request and simulates handing it to an email or SMS provider.

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/notifications` | Queue a notification, returns `202` |

```
curl -X POST localhost:8000/api/notifications \
  -H 'Content-Type: application/json' \
  -d '{"order_id":1,"channel":"sms","event":"shipped"}'
```

## Telemetry

Started with `opentelemetry-instrument`. Set:

| Variable | Example |
|---|---|
| `OTEL_SERVICE_NAME` | `notification` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://otel-collector:4318` |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | `http/protobuf` |

## Run locally

```
pip install -r requirements.txt
uvicorn app.main:app --port 8004
```
