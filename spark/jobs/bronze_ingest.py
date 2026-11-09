"""Bronze ingest: Kafka otel.traces -> Parquet on MinIO, partitioned by date and hour.

The payload is kept as the raw OTLP JSON string. Parsing happens in Silver, so Bronze can
always be replayed.

Run: bash /opt/tracelake/spark/submit.sh bronze_ingest
"""

from __future__ import annotations

import argparse
import os

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from common.spark_session import get_spark


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--topic", default="otel.traces")
    p.add_argument("--bootstrap", default=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"))
    p.add_argument("--output", default="s3a://bronze/otel_traces")
    p.add_argument("--checkpoint", default="s3a://checkpoints/bronze_otel_traces")
    p.add_argument("--trigger", default="30 seconds")
    p.add_argument("--starting-offsets", default="earliest")
    p.add_argument("--max-offsets", default="50000", help="maxOffsetsPerTrigger")
    return p.parse_args()


def to_bronze(raw: DataFrame) -> DataFrame:
    """Kafka rows -> Bronze rows. Kept separate so it can be unit tested."""
    return raw.select(
        F.col("key").cast("string").alias("kafka_key"),
        F.col("value").cast("string").alias("payload"),
        F.col("topic"),
        F.col("partition").alias("kafka_partition"),
        F.col("offset").alias("kafka_offset"),
        F.col("timestamp").alias("kafka_ts"),
        F.current_timestamp().alias("ingested_at"),
        F.date_format("timestamp", "yyyy-MM-dd").alias("date"),
        F.date_format("timestamp", "HH").alias("hour"),
    )


def main() -> None:
    args = parse_args()
    spark = get_spark("bronze_ingest", with_hudi=False)
    spark.sparkContext.setLogLevel("WARN")

    raw = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", args.bootstrap)
        .option("subscribe", args.topic)
        .option("startingOffsets", args.starting_offsets)
        .option("maxOffsetsPerTrigger", args.max_offsets)
        .option("failOnDataLoss", "false")
        .load()
    )

    query = (
        to_bronze(raw)
        .writeStream.format("parquet")
        .option("path", args.output)
        .option("checkpointLocation", args.checkpoint)
        .partitionBy("date", "hour")
        .outputMode("append")
        .trigger(processingTime=args.trigger)
        .queryName("bronze_otel_traces")
        .start()
    )
    query.awaitTermination()


if __name__ == "__main__":
    main()
