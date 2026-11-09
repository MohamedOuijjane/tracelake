#!/usr/bin/env bash
# Create tracelake topics. Safe to run many times.
# Runs inside the kafka container (make topics) or the kafka-init job.
set -euo pipefail

BOOTSTRAP="${KAFKA_BOOTSTRAP_SERVERS:-localhost:9092}"
KT=/opt/kafka/bin/kafka-topics.sh
# Keep the CLI JVM small, it shares the container with the broker.
export KAFKA_HEAP_OPTS="-Xmx128m"

HOUR=3600000
DAY=$((24 * HOUR))

# name partitions retention_ms
TOPICS=(
  "otel.traces 6 $((3 * DAY))"
  "otel.metrics 3 $((3 * DAY))"
  "otel.logs 3 $((1 * DAY))"
  "alerts 1 $((7 * DAY))"
  "dlq 1 $((14 * DAY))"
)

for entry in "${TOPICS[@]}"; do
  read -r name partitions retention <<<"$entry"
  "$KT" --bootstrap-server "$BOOTSTRAP" --create --if-not-exists \
    --topic "$name" \
    --partitions "$partitions" \
    --replication-factor 1 \
    --config retention.ms="$retention" \
    --config compression.type=producer
  echo "topic ready: $name (partitions=$partitions retention.ms=$retention)"
done

"$KT" --bootstrap-server "$BOOTSTRAP" --list
