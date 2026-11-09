# gateway

Edge service built on Spring Cloud Gateway (Spring Boot 3.4, Java 21). All load test traffic enters here.

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/actuator/health` | Health check |
| GET | `/api/catalog` | Static product list (business endpoint) |
| any | `/api/orders/**` | Routed to `orders` |
| any | `/api/payments/**` | Routed to `payments` |
| any | `/api/inventory/**` | Routed to `inventory` |
| any | `/api/notifications/**` | Routed to `notification` |

The `/api` prefix is stripped before forwarding.

## Telemetry

The OpenTelemetry Java agent is attached through `JAVA_TOOL_OPTIONS` in the Dockerfile. Configure it with env vars:

| Variable | Example |
|---|---|
| `OTEL_SERVICE_NAME` | `gateway` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://otel-collector:4318` |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | `http/protobuf` |

## Config

| Variable | Default |
|---|---|
| `ORDERS_URL` | `http://localhost:8081` |
| `PAYMENTS_URL` | `http://localhost:8002` |
| `INVENTORY_URL` | `http://localhost:8003` |
| `NOTIFICATION_URL` | `http://localhost:8004` |

## Run

```
docker compose --profile full up -d gateway
curl localhost:8000/api/catalog
```
