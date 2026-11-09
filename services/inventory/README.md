# inventory

Inventory service in Go (1.23, standard library router). Stock is kept in memory and resets on restart.

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/inventory/{sku}` | Available stock for a SKU |
| POST | `/inventory/reserve` | Reserve stock, body `{"sku":"SKU-001","quantity":1}` |

`/reserve` returns `409` when stock is too low. `orders` calls it before saving an order.

## Telemetry

Go has no runtime agent, so the service sets up the OTel SDK in `initTracer` and wraps the router with `otelhttp`. The SDK reads standard env vars:

| Variable | Example |
|---|---|
| `OTEL_SERVICE_NAME` | `inventory` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://otel-collector:4318` |

## Run locally

```
go run .
curl localhost:8080/inventory/SKU-001
```
