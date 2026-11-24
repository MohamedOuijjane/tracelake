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

## Fault injection (chaos F2)

When `CHAOS_ENABLED=true` (set in `docker-compose.yml`), the service also serves an internal admin endpoint. It is not published to the host and the gateway does not route `/admin`, so only containers on the docker network can reach it.

| Method | Path | Description |
|---|---|---|
| POST | `/admin/fault` | Set the error rate, body `{"error_rate": 0.3}` (0 to 1) |
| DELETE | `/admin/fault` | Clear the fault (error rate 0) |
| GET | `/admin/fault` | Show the current error rate |

While the error rate is above 0, that share of the `menu` and `check` requests answers `503` with `{"error":"injected fault F2"}`. The SERVER span of a failed request has status `ERROR` with description `injected fault F2` and the attribute `chaos.fault=F2`. `/health` is never affected.

A failed request gets its SERVER span from a small layer in front of `otelhttp` ([fault.go](fault.go)): `otelhttp` sets the span status from the response code after the handler returns and would replace the description with an empty one. The span keeps the route name and continues the caller's trace.

`make chaos FAULT=F2` and `make heal` drive this endpoint, see [loadgen/chaos](../../loadgen/chaos/README.md).

## Telemetry

Go has no runtime agent, so the service sets up the OTel SDK in `initTracer` and wraps each business route with `otelhttp`, which emits a `SERVER` span named after the route and reads the W3C `traceparent` header sent by `orders`. The SDK reads standard env vars:

| Variable | Example |
|---|---|
| `OTEL_SERVICE_NAME` | `restaurants` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://otel-collector:4318` |

## Run locally

```
go run .
curl localhost:8080/restaurants/1/menu
```
