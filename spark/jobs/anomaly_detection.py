"""Anomaly detection on RED metrics with MLlib KMeans.

Idea: cluster normal (service, minute) points. A point far from its nearest centroid is an
anomaly. Distances above the threshold are published to the Kafka alerts topic.

Skeleton. Training and scoring run; threshold tuning and model storage are TODO.

Run: bash /opt/tracelake/spark/submit.sh anomaly_detection --train-days 7
"""

from __future__ import annotations

import argparse
import os

from pyspark.ml import Pipeline, PipelineModel
from pyspark.ml.clustering import KMeans
from pyspark.ml.feature import StandardScaler, VectorAssembler
from pyspark.ml.functions import vector_to_array
from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from common.spark_session import get_spark

FEATURES = ["request_rate", "error_rate", "p50_ms", "p95_ms", "p99_ms"]


def build_pipeline(k: int, seed: int = 42) -> Pipeline:
    return Pipeline(
        stages=[
            VectorAssembler(inputCols=FEATURES, outputCol="raw", handleInvalid="skip"),
            StandardScaler(inputCol="raw", outputCol="features", withMean=True, withStd=True),
            KMeans(k=k, seed=seed, featuresCol="features", predictionCol="cluster"),
        ]
    )


def score(model: PipelineModel, df: DataFrame) -> DataFrame:
    """Add distance to the assigned centroid."""
    centers = model.stages[-1].clusterCenters()
    spark = df.sparkSession
    centers_df = spark.createDataFrame(
        [(i, [float(x) for x in c]) for i, c in enumerate(centers)], ["cluster", "center"]
    )
    scored = model.transform(df).withColumn("fvec", vector_to_array("features"))
    return scored.join(F.broadcast(centers_df), "cluster").withColumn(
        "distance",
        F.sqrt(
            F.aggregate(
                F.zip_with("fvec", "center", lambda a, b: (a - b) * (a - b)),
                F.lit(0.0),
                lambda acc, x: acc + x,
            )
        ),
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--red", default="s3a://gold/red_metrics")
    p.add_argument("--model-path", default="s3a://gold/models/red_kmeans")
    p.add_argument("--train-days", type=int, default=7)
    p.add_argument("--k", type=int, default=4)
    p.add_argument("--threshold", type=float, default=3.0, help="distance in std units")
    p.add_argument("--bootstrap", default=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"))
    p.add_argument("--alerts-topic", default="alerts")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    spark = get_spark("anomaly_detection")
    red = spark.read.format("hudi").load(args.red)

    cutoff = F.date_sub(F.current_date(), args.train_days)
    train = red.where(F.col("minute") >= cutoff)
    # TODO: load the model trained by the model_retrain DAG instead of fitting every run.
    model = build_pipeline(args.k).fit(train)
    model.write().overwrite().save(args.model_path)

    recent = red.where(F.col("minute") >= F.expr("current_timestamp() - INTERVAL 15 MINUTES"))
    anomalies = score(model, recent).where(F.col("distance") > args.threshold)

    alerts = anomalies.select(
        F.col("service").alias("key"),
        F.to_json(
            F.struct("service", "minute", "distance", *FEATURES, F.lit("kmeans").alias("detector"))
        ).alias("value"),
    )
    (
        alerts.write.format("kafka")
        .option("kafka.bootstrap.servers", args.bootstrap)
        .option("topic", args.alerts_topic)
        .save()
    )
    # TODO: tune threshold per cluster (for example p99.5 of training distances).


if __name__ == "__main__":
    main()
