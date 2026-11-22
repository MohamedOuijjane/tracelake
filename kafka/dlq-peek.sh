#!/usr/bin/env bash
# Print the last N messages (default 10) of otel.traces.dlq across all partitions, oldest first.
# Runs inside the kafka container (make dlq-peek).
set -euo pipefail

BOOTSTRAP="${KAFKA_BOOTSTRAP_SERVERS:-localhost:9092}"
TOPIC="${TOPIC:-otel.traces.dlq}"
N="${1:-10}"
BIN=/opt/kafka/bin
# Keep the CLI JVM small, it shares the container with the broker.
export KAFKA_HEAP_OPTS="-Xmx128m"

# Lines look like otel.traces.dlq:0:42 (topic:partition:end offset).
offsets=$("$BIN/kafka-get-offsets.sh" --bootstrap-server "$BOOTSTRAP" --topic "$TOPIC" --time -1)

{
  while IFS=: read -r _ partition end; do
    [ "$end" -gt 0 ] || continue
    start=$((end > N ? end - N : 0))
    "$BIN/kafka-console-consumer.sh" --bootstrap-server "$BOOTSTRAP" --topic "$TOPIC" \
      --partition "$partition" --offset "$start" --max-messages $((end - start)) \
      --timeout-ms 10000 --property print.timestamp=true --property print.partition=true \
      2>/dev/null || true
  done <<<"$offsets"
} | sort -t: -k2 -n | tail -n "$N"

total=$(awk -F: '{s += $3} END {print s + 0}' <<<"$offsets")
echo "--- $TOPIC holds $total messages" >&2
