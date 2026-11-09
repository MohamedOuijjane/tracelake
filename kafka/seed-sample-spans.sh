#!/usr/bin/env bash
# Push a few OTLP JSON trace messages to otel.traces so Bronze has data without the services.
set -euo pipefail

BOOTSTRAP="${KAFKA_BOOTSTRAP_SERVERS:-localhost:9092}"
export KAFKA_HEAP_OPTS="-Xmx128m"
COUNT="${1:-20}"

now_ns() { echo "$(date +%s)000000000"; }

for i in $(seq 1 "$COUNT"); do
  trace_id=$(printf '%032x' $((RANDOM * RANDOM + i)))
  start=$(now_ns)
  end=$((start + (RANDOM % 300 + 5) * 1000000))
  status=1
  if (( RANDOM % 20 == 0 )); then status=2; fi
  printf '{"resourceSpans":[{"resource":{"attributes":[{"key":"service.name","value":{"stringValue":"orders"}}]},"scopeSpans":[{"scope":{"name":"seed"},"spans":[{"traceId":"%s","spanId":"%016x","parentSpanId":"","name":"POST /orders","kind":2,"startTimeUnixNano":"%s","endTimeUnixNano":"%s","attributes":[{"key":"http.request.method","value":{"stringValue":"POST"}}],"status":{"code":%d}}]}]}]}\n' \
    "$trace_id" "$i" "$start" "$end" "$status"
done | /opt/kafka/bin/kafka-console-producer.sh --bootstrap-server "$BOOTSTRAP" --topic otel.traces

echo "sent $COUNT sample traces to otel.traces"
