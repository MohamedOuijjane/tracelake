# Hudi table design

All tables live on MinIO and are written by Spark with the `hudi-spark3.5-bundle_2.12:1.0.2` bundle. Trino reads them through the `hudi` catalog.

## Buckets

| Bucket | Content |
|---|---|
| `bronze` | Raw Kafka payloads as Parquet, partitioned by `date` and `hour` |
| `silver` | Cleaned, keyed Hudi tables |
| `gold` | Aggregates for dashboards and models, plus `_metastore` for Trino |
| `checkpoints` | Spark Structured Streaming checkpoints |

## Silver

### `silver.spans`

| Setting | Value |
|---|---|
| Path | `s3a://silver/spans` |
| Type | Merge on Read |
| Record key | `trace_id`, `span_id` |
| Precombine | `end_ts` |
| Partition | `date` (from `start_ts`) |
| Key generator | `ComplexKeyGenerator` |
| Schema | [contracts/span.avsc](../../contracts/span.avsc) plus `end_ts`, `kind`, `date` |

MoR because spans arrive in many small batches and can be duplicated. See [ADR 0002](../../docs/adr/0002-hudi-merge-on-read-for-spans.md).

### `silver.service_calls`

One row per parent and child span pair where the services differ, so it is an edge in the call graph.

| Column | Type |
|---|---|
| `trace_id` | string |
| `caller` | string (parent span service) |
| `callee` | string (child span service) |
| `operation` | string |
| `start_ts` | timestamp |
| `duration_ms` | double |
| `is_error` | boolean |
| `date` | string, partition |

Type: MoR, key `trace_id` + child `span_id`.

### `silver.metrics`

Flattened OTLP metric points, schema [contracts/metric.avsc](../../contracts/metric.avsc). Type: MoR, key `service`, `metric_name`, `ts`, `attr_hash`, partition `date`.

## Gold

All Gold tables are Copy on Write: small, read heavy, rewritten per window.

### `gold.red_metrics`

| Column | Type | Notes |
|---|---|---|
| `service` | string | key |
| `minute` | timestamp | key, window start |
| `request_count` | long | |
| `request_rate` | double | requests per second |
| `error_count` | long | spans with status ERROR |
| `error_rate` | double | error_count / request_count |
| `p50_ms`, `p95_ms`, `p99_ms` | double | `percentile_approx` on server spans |
| `date` | string | partition |

### `gold.slo`

Per service and SLO window (1 h, 6 h, 24 h, 30 d): target, good events, total events, error budget remaining, burn rate. Key `service`, `slo_name`, `window`, `window_end`.

### `gold.dependency_graph`

Per day: `caller`, `callee`, `call_count`, `error_rate`, `p95_ms`. Built from `silver.service_calls`. Key `date`, `caller`, `callee`.

## Registering tables in Trino

The Trino Hudi connector is read only: it reads tables that a metastore already knows, and cannot create schemas or tables itself. The scaffold wires the catalog to a file metastore so Trino starts, but no tables are listed yet.

Plan (Core pipeline milestone):

1. Add a Hive Metastore service (Postgres backed) to the `full` profile.
2. Switch [hudi.properties](../trino/catalog/hudi.properties) to `hive.metastore=thrift`.
3. Turn on Hudi hive sync in the Spark writers (`hoodie.datasource.hive_sync.enable=true`, `mode=hms`).

Check what Trino sees:

```
docker compose exec trino trino --execute "SHOW SCHEMAS FROM hudi"
```
