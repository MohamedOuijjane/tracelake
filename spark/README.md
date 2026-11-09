# spark

PySpark jobs for the lakehouse. Spark 3.5.5, Scala 2.12, Hudi 1.0.2.

| Job | Mode | Input | Output |
|---|---|---|---|
| [bronze_ingest.py](jobs/bronze_ingest.py) | Structured Streaming | Kafka `otel.traces` | `s3a://bronze/otel_traces` |
| [silver_spans.py](jobs/silver_spans.py) | batch | Bronze | `s3a://silver/spans` (Hudi MoR) |
| [gold_red_metrics.py](jobs/gold_red_metrics.py) | batch | Silver spans | `s3a://gold/red_metrics` |
| [anomaly_detection.py](jobs/anomaly_detection.py) | batch, MLlib | Gold RED | Kafka `alerts` |

[common/spark_session.py](common/spark_session.py) builds every session with the Hudi, Kafka and S3A settings. Change versions there and in [submit.sh](submit.sh) together.

## Run on the local cluster

```
make up
make topics
make bronze                     # starts the streaming job in the background
docker compose exec spark-master bash /opt/tracelake/spark/submit.sh silver_spans
```

## Tests

Tests run Spark in local mode without Hudi or S3 jars. Java 17 is required.

```
pip install -r requirements.txt
pytest -q
```
