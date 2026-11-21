# delivery

Delivery service on FastAPI (Python 3.12). It assigns a courier to a paid order and estimates when the food arrives.

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/deliveries` | Assign a courier, returns `201` with the courier id and ETA |

```
curl -X POST localhost:8000/deliveries \
  -H 'Content-Type: application/json' \
  -d '{"order_id":1,"restaurant_id":"1","preparation_minutes":14,"address":"12 Rue de la Paix"}'
```

```
{"delivery_id":"...","order_id":1,"courier_id":"courier-017","eta_minutes":31,"status":"ASSIGNED"}
```

The ETA is the longer of the preparation time and the courier's ride to the restaurant, plus the ride to the customer. `orders` calls this endpoint after the payment succeeds. The service is not exposed through the gateway.

## Telemetry

Started with `opentelemetry-instrument`. FastAPI is instrumented automatically and emits a `SERVER` span that continues the W3C `traceparent` sent by `orders`. Set:

| Variable | Example |
|---|---|
| `OTEL_SERVICE_NAME` | `delivery` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://otel-collector:4318` |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | `http/protobuf` |

## Run locally

```
pip install -r requirements.txt
uvicorn app.main:app --port 8004
```
