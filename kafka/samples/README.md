# samples

`otel-traces-sample.jsonl` holds 200 messages taken from the `otel.traces` topic while k6 was running against the full profile.

Format: one OTLP JSON `ExportTraceServiceRequest` per line, as written by the collector. Spans are grouped by `resourceSpans` and `scopeSpans`, and the service name is in the `service.name` resource attribute.

The fields we keep after flattening are defined in [contracts/span.avsc](../../contracts/span.avsc).

Use it to test the Spark jobs, especially `silver_spans.py`, on real data without starting the whole platform.

Regenerate it with the full profile and k6 running:

```
docker compose exec -T kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 --topic otel.traces \
  --from-beginning --max-messages 200 --timeout-ms 15000 \
  > kafka/samples/otel-traces-sample.jsonl
```
