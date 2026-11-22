# kafka

Single Kafka 3.9.1 broker in KRaft mode (no ZooKeeper). Auto topic creation is off, so topics come from [create-topics.sh](create-topics.sh), run by the `kafka-init` job at startup and by `make topics`.

| Topic | Partitions | Retention | Producer |
|---|---|---|---|
| `otel.traces` | 6 | 3 days | OTel Collector |
| `otel.traces.dlq` | 3 | 7 days | Spark Bronze job, records it cannot parse |
| `otel.metrics` | 3 | 3 days | OTel Collector |
| `otel.logs` | 3 | 1 day | OTel Collector |
| `alerts` | 1 | 7 days | `anomaly_detection.py` |
| `dlq` | 1 | 14 days | Spark jobs, unparseable records |

`make seed` pushes sample OTLP JSON spans to `otel.traces` with [seed-sample-spans.sh](seed-sample-spans.sh), useful with the `core` profile only.

## Dead letter topic

`otel.traces.dlq` holds the `otel.traces` messages that the Spark Bronze job cannot parse. The job writes them there with the error reason and keeps going, instead of stopping the stream on one bad record. They can then be inspected and replayed.

Each DLQ message is one JSON object:

| Field | Content |
|---|---|
| `value` | Original message value, as a string |
| `error` | Why parsing failed |
| `source_topic` | Topic the message came from, `otel.traces` |
| `source_partition` | Partition of the original message |
| `source_offset` | Offset of the original message |
| `timestamp` | When the job rejected it, UTC ISO 8601 |

This folder only creates the topic. Writing to it is done by the Bronze job and is owned by the processing layer (`spark/`).

| Command | What it does |
|---|---|
| `make bad-message` | Sends one non JSON message to `otel.traces` to exercise the DLQ path |
| `make dlq-peek` | Prints the last 10 messages of `otel.traces.dlq`, with their timestamps, using [dlq-peek.sh](dlq-peek.sh) |

Read from the host:

```
docker compose exec kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 --topic otel.traces --max-messages 1
```
