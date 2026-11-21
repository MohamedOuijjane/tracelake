# restaurants

Restaurant service in Go (1.23, standard library router). Menus are static and kept in memory.

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check (not traced) |
| GET | `/restaurants/{id}/menu` | Menu of a restaurant, `404` if unknown |
| POST | `/restaurants/{id}/check` | Check that dishes are available and estimate the preparation time |

Restaurants `1` to `4` exist. Each menu has one dish marked unavailable, so some orders are refused.

Check request:

```
curl -X POST localhost:8080/restaurants/1/check \
  -H 'Content-Type: application/json' \
  -d '{"items":[{"dish_id":"pz-margherita","quantity":2}]}'
```

Response `200`:

```
{"restaurant_id":"1","available":true,"total":19,"preparation_minutes":14}
```

`409` lists the dishes that are unknown or unavailable. `orders` calls this endpoint first when an order is placed.

Each request sleeps a few tens of milliseconds to simulate the restaurant backend.

## Telemetry

Go has no runtime agent, so the service sets up the OTel SDK in `initTracer` and wraps each route with `otelhttp`, which emits a `SERVER` span named after the route and reads the W3C `traceparent` header sent by `orders`. The SDK reads standard env vars:

| Variable | Example |
|---|---|
| `OTEL_SERVICE_NAME` | `restaurants` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://otel-collector:4318` |

## Run locally

```
go run .
curl localhost:8080/restaurants/1/menu
```
