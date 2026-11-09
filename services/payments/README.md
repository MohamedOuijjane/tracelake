# payments

Payment service on FastAPI (Python 3.12). It simulates a card processor with random latency and a configurable failure rate, then calls `notification`.

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/payments` | Charge an order |

```
curl -X POST localhost:8000/api/payments \
  -H 'Content-Type: application/json' \
  -d '{"order_id":1,"amount":49.9}'
```

Returns `201` with a payment id, or `502` when the simulated processor declines.

## Telemetry

Started with `opentelemetry-instrument`. FastAPI and httpx are instrumented automatically. Set:

| Variable | Example |
|---|---|
| `OTEL_SERVICE_NAME` | `payments` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://otel-collector:4318` |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | `http/protobuf` |

## Config

| Variable | Default |
|---|---|
| `NOTIFICATION_URL` | `http://localhost:8004` |
| `PAYMENT_FAILURE_RATE` | `0.05` |

## Run locally

```
pip install -r requirements.txt
uvicorn app.main:app --port 8002
```
