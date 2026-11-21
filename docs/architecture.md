# Architecture

## Data flow

```mermaid
flowchart TD
  k6[k6 loadgen] -->|HTTP| gw[gateway :8080]
  gw -->|/api/menu| rest[restaurants]
  gw -->|/api/orders| ord[orders]
  gw -->|/api/payments| pay[payments]
  ord -->|1 check dishes| rest
  ord -->|2 charge| pay
  ord -->|3 assign courier| del[delivery]
  ord -->|JDBC| pg[(postgres)]

  gw & ord & rest & pay & del -->|OTLP HTTP :4318| col[OTel Collector]

  col -->|kafka exporter, otlp_json<br/>keyed by trace id| t1[[otel.traces]]
  col --> t2[[otel.metrics]]
  col --> t3[[otel.logs]]

  t1 -->|bronze_ingest.py<br/>Structured Streaming| b[(s3a://bronze/otel_traces<br/>Parquet, date/hour)]
  t2 -.->|TODO| bm[(s3a://bronze/otel_metrics)]
  b -->|silver_spans.py<br/>Hudi MoR upsert| s[(s3a://silver/spans)]
  s --> sc[(s3a://silver/service_calls)]
  bm -.-> sm[(s3a://silver/metrics)]
  s -->|gold_red_metrics.py| g1[(s3a://gold/red_metrics)]
  g1 --> g2[(s3a://gold/slo)]
  sc --> g3[(s3a://gold/dependency_graph)]
  g1 -->|anomaly_detection.py<br/>MLlib KMeans| al[[alerts]]

  g1 & g2 & g3 & s --> trino[Trino hudi catalog]
  trino --> graf[Grafana]

  af[Airflow] -.->|daily report| g1
  af -.->|compaction, cleaning| s
  af -.->|weekly retrain| al
  af -.->|data quality| b
```

## One order, one trace

`POST /api/orders` enters the gateway and fans out from `orders`:

```
gateway      SERVER  POST orders
gateway      CLIENT  POST
orders       SERVER  POST /orders
orders       CLIENT  POST          -> restaurants  SERVER  POST /restaurants/{id}/check
orders       CLIENT  INSERT orders.food_orders
orders       CLIENT  POST          -> payments     SERVER  POST /payments
orders       CLIENT  POST          -> delivery     SERVER  POST /deliveries
orders       CLIENT  UPDATE orders.food_orders
```

This is a simplified view of a real trace: the agents also add `INTERNAL` spans for Spring Data, Hibernate and the ASGI send and receive steps.

The Java agent (gateway, orders), `otelhttp` (restaurants) and `opentelemetry-instrument` (payments, delivery) all use the W3C `traceparent` header (`OTEL_PROPAGATORS=tracecontext,baggage`), so every span shares one `trace_id`. The collector sets `partition_traces_by_id`, so all spans of a trace land in the same `otel.traces` partition. Silver keeps the span kind, which Gold uses to count only `SERVER` spans in RED metrics and to pair `CLIENT` and `SERVER` spans in the dependency graph.

## Layers

| Layer | Location | Format | Written by |
|---|---|---|---|
| Raw stream | Kafka `otel.*` | OTLP JSON | OTel Collector |
| Bronze | `s3a://bronze/` | Parquet, partitioned by `date`, `hour` | `bronze_ingest.py` |
| Silver | `s3a://silver/` | Hudi Merge on Read | `silver_spans.py` |
| Gold | `s3a://gold/` | Hudi Copy on Write | `gold_*.py` |
| Checkpoints | `s3a://checkpoints/` | Spark streaming state | all streaming jobs |

Bronze keeps the payload exactly as it arrived, plus Kafka metadata. Nothing is parsed there, so we can replay Silver at any time.

Silver flattens `resourceSpans[].scopeSpans[].spans[]` into one row per span matching [contracts/span.avsc](../contracts/span.avsc).

Gold holds small, query ready tables that Grafana reads through Trino.

## Runtime

Everything runs from [docker-compose.yml](../docker-compose.yml). Profiles:

- `core`: Kafka, MinIO (plus bucket init), Spark master and worker.
- `full`: core + collector, services, Postgres, Airflow, Trino, Grafana.
- `demo`: full + k6.

Spark jobs are submitted to `spark://spark-master:7077` from the master container. The shared builder in [spark/common/spark_session.py](../spark/common/spark_session.py) sets the Hudi, Kafka and S3A packages and MinIO endpoint.

## Decisions

See [adr/](adr/).
