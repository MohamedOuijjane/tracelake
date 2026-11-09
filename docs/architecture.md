# Architecture

## Data flow

```mermaid
flowchart TD
  k6[k6 loadgen] -->|HTTP| gw[gateway :8080]
  gw -->|/api/orders| ord[orders]
  gw -->|/api/payments| pay[payments]
  gw -->|/api/inventory| inv[inventory]
  ord -->|reserve stock| inv
  ord -->|JDBC| pg[(postgres)]
  pay -->|notify| notif[notification]

  gw & ord & pay & inv & notif -->|OTLP HTTP :4318| col[OTel Collector]

  col -->|kafka exporter, otlp_json| t1[[otel.traces]]
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
