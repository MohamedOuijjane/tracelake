# orders

Order service on Spring Boot 3.4 (Java 21) with PostgreSQL through Spring Data JPA.

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/actuator/health` | Health check, includes the database |
| POST | `/orders` | Place an order: reserves stock in `inventory`, stores the order |
| GET | `/orders/{id}` | Fetch an order |

Example:

```
curl -X POST localhost:8000/api/orders \
  -H 'Content-Type: application/json' \
  -d '{"sku":"SKU-001","quantity":1}'
```

Returns `201` when stock was reserved, `409` when inventory refused.

## Telemetry

The OpenTelemetry Java agent instruments Spring MVC, JDBC and the outgoing `RestClient` call. Set:

| Variable | Example |
|---|---|
| `OTEL_SERVICE_NAME` | `orders` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://otel-collector:4318` |

## Config

| Variable | Description |
|---|---|
| `SPRING_DATASOURCE_URL` | JDBC URL of Postgres |
| `SPRING_DATASOURCE_USERNAME` | DB user |
| `SPRING_DATASOURCE_PASSWORD` | DB password |
| `INVENTORY_URL` | Base URL of the inventory service |

The schema is created by Hibernate (`ddl-auto: update`). Replace with Flyway before v1.0.
