# Contracts

Avro schemas for the rows we store after flattening OTLP data. They are the agreement between the Spark jobs (writers) and Trino, Grafana and the anomaly job (readers).

| File | Table | Key |
|---|---|---|
| [span.avsc](span.avsc) | `silver.spans` | `trace_id` + `span_id` |
| [metric.avsc](metric.avsc) | `silver.metrics` | `service` + `metric_name` + `ts` + attributes hash |

Kafka topics carry raw OTLP JSON from the collector, not these schemas. The mapping happens in Silver:

| Contract field | OTLP JSON path |
|---|---|
| `trace_id` | `resourceSpans[].scopeSpans[].spans[].traceId` |
| `span_id` | `...spans[].spanId` |
| `parent_span_id` | `...spans[].parentSpanId` (empty string becomes null) |
| `service` | `resourceSpans[].resource.attributes[key=service.name]` |
| `operation` | `...spans[].name` |
| `start_ts` | `...spans[].startTimeUnixNano` |
| `duration_ms` | `(endTimeUnixNano - startTimeUnixNano) / 1e6` |
| `status_code` | `...spans[].status.code` (0 UNSET, 1 OK, 2 ERROR) |
| `attributes` | `...spans[].attributes[]` as a string map |

## Rules for changes

- Only add fields with a default. Never rename or remove a field in place.
- Breaking changes need a new record name (for example `SpanV2`) and an ADR.
- Update the Silver job and this README in the same PR.

Validate a schema locally:

```
python -c "import json,sys; json.load(open('contracts/span.avsc'))"
```
