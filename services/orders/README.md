# orders

Order service on Spring Boot 3.4 (Java 21) with PostgreSQL through Spring Data JPA. It drives the food order flow.

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/actuator/health` | Health check, includes the database |
| POST | `/orders` | Place a food order |
| GET | `/orders/{id}` | Fetch an order |

`POST /orders` calls the other services in this order:

1. `restaurants` `POST /restaurants/{id}/check`: dishes available, total price, preparation time.
2. `payments` `POST /payments`: charge the total.
3. `delivery` `POST /deliveries`: assign a courier, get an ETA.

The order is stored in the `food_orders` table once the restaurant accepts it, then updated after the payment and the delivery.

Example:

```
curl -X POST localhost:8000/api/orders \
  -H 'Content-Type: application/json' \
  -d '{"restaurant_id":"1","items":[{"dish_id":"pz-margherita","quantity":2}],"address":"12 Rue de la Paix"}'
```

| Code | Status | Meaning |
|---|---|---|
| `201` | `CONFIRMED` | Paid, courier assigned, `courier_id` and `eta_minutes` set |
| `202` | `AWAITING_COURIER` | Paid, but delivery did not answer |
| `402` | `PAYMENT_FAILED` | The card processor declined |
| `409` | `REJECTED` | A dish is unknown or unavailable |
| `404` | | Unknown restaurant, nothing stored |

Each request also sleeps 5 to 25 ms to simulate validation.

## Telemetry

The OpenTelemetry Java agent instruments Spring MVC (`SERVER` span), JDBC, and the three outgoing `RestClient` calls (`CLIENT` spans). The agent injects the W3C `traceparent` header on each call, so restaurants, payments and delivery join the trace that started at the gateway. Set:

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
| `RESTAURANTS_URL` | Base URL of the restaurants service |
| `PAYMENTS_URL` | Base URL of the payments service |
| `DELIVERY_URL` | Base URL of the delivery service |

The schema is created by Hibernate (`ddl-auto: update`). Replace with Flyway before v1.0.
