# kafka

Single Kafka 3.9.1 broker in KRaft mode (no ZooKeeper). Auto topic creation is off, so topics come from [create-topics.sh](create-topics.sh), run by the `kafka-init` job at startup and by `make topics`.

| Topic | Partitions | Retention | Producer |
|---|---|---|---|
| `otel.traces` | 6 | 3 days | OTel Collector |
| `otel.metrics` | 3 | 3 days | OTel Collector |
| `otel.logs` | 3 | 1 day | OTel Collector |
| `alerts` | 1 | 7 days | `anomaly_detection.py` |
| `dlq` | 1 | 14 days | Spark jobs, unparseable records |

`make seed` pushes sample OTLP JSON spans to `otel.traces` with [seed-sample-spans.sh](seed-sample-spans.sh), useful with the `core` profile only.

Read from the host:

```
docker compose exec kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 --topic otel.traces --max-messages 1
```
