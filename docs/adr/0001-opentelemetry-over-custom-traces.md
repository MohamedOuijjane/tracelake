# ADR 0001: OpenTelemetry over custom trace format

- Status: accepted
- Date: 2026-11-09
- Owners: @member1

## Context

We have services in Java, Python and Go. We need traces and metrics from all of them with the same IDs, the same propagation headers and the same field names, without writing tracing code in each service.

## Decision

Use OpenTelemetry everywhere:

- Java: the OTel Java agent, attached with `JAVA_TOOL_OPTIONS`.
- Python: `opentelemetry-instrument` from `opentelemetry-distro`.
- Go: the OTel SDK with `otelhttp` (Go has no runtime agent).

Services are configured only through standard env vars (`OTEL_SERVICE_NAME`, `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_PROTOCOL`). They send OTLP to one collector, which owns batching and the Kafka export.

## Options considered

1. Custom JSON spans posted to Kafka by each service. Full control, but we would maintain three client libraries and context propagation by hand.
2. Zipkin or Jaeger clients. Mature, but both projects now point users to OTel, and metrics would need a separate path.
3. OpenTelemetry. One spec for traces, metrics and logs, W3C trace context, vendor neutral collector.

## Consequences

- No tracing code in business logic for Java and Python.
- The collector is a single point to change export format or add sampling.
- We depend on the OTLP JSON shape in Kafka. Silver parsing must follow OTLP releases.
