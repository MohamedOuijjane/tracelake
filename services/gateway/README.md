# gateway

Edge service built on Spring Cloud Gateway (Spring Boot 3.4, Java 21). All load test traffic enters here.

## Endpoints

| Method | Path | Routed to |
|---|---|---|
| GET | `/actuator/health` | Health check, not routed |
| GET | `/api/menu/{id}` | `restaurants` `GET /restaurants/{id}/menu` |
| any | `/api/orders/**` | `orders`, `/api` prefix stripped |
| any | `/api/payments/**` | `payments`, `/api` prefix stripped (direct charges such as tips) |

`delivery` is internal: only `orders` calls it.

A global filter adds a 2 to 15 ms non blocking delay before each routed request to stand in for auth and rate limiting.

## Telemetry

The OpenTelemetry Java agent is attached through `JAVA_TOOL_OPTIONS` in the Dockerfile. It emits a `SERVER` span for the incoming request and a `CLIENT` span for the proxied call, and injects the W3C `traceparent` header so the downstream service continues the trace. Configure it with env vars:

| Variable | Example |
|---|---|
| `OTEL_SERVICE_NAME` | `gateway` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://otel-collector:4318` |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | `http/protobuf` |

## Config

| Variable | Default |
|---|---|
| `RESTAURANTS_URL` | `http://localhost:8003` |
| `ORDERS_URL` | `http://localhost:8081` |
| `PAYMENTS_URL` | `http://localhost:8002` |

## Run

```
docker compose --profile full up -d gateway
curl localhost:8000/api/menu/1
```
