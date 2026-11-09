# otel

OpenTelemetry Collector (contrib 0.120.0) config and image.

| Port | Purpose |
|---|---|
| 4317 | OTLP gRPC |
| 4318 | OTLP HTTP (services use this) |
| 13133 | health_check extension |

Pipelines:

| Signal | Kafka topic | Encoding |
|---|---|---|
| traces | `otel.traces` | `otlp_json` |
| metrics | `otel.metrics` | `otlp_json` |
| logs | `otel.logs` | `otlp_json` |

Each Kafka message is one OTLP export request (`resourceSpans`, `resourceMetrics` or `resourceLogs`) serialized as JSON.

Validate the config:

```
docker run --rm -v "$PWD/otel:/cfg" otel/opentelemetry-collector-contrib:0.120.0 validate --config=/cfg/collector-config.yaml
```
