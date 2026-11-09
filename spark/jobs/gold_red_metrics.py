"""Gold RED metrics: rate, error rate and p50/p95/p99 latency per service per minute.

Skeleton. The aggregation is complete; scheduling and incremental windows are TODO.

Run: bash /opt/tracelake/spark/submit.sh gold_red_metrics --date 2026-11-09
"""

from __future__ import annotations

import argparse

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from common.spark_session import get_spark

SPAN_KIND_SERVER = 2

HUDI_OPTIONS = {
    "hoodie.table.name": "red_metrics",
    "hoodie.datasource.write.table.type": "COPY_ON_WRITE",
    "hoodie.datasource.write.operation": "upsert",
    "hoodie.datasource.write.recordkey.field": "service,minute",
    "hoodie.datasource.write.precombine.field": "computed_at",
    "hoodie.datasource.write.partitionpath.field": "date",
    "hoodie.datasource.write.keygenerator.class": "org.apache.hudi.keygen.ComplexKeyGenerator",
    "hoodie.datasource.write.hive_style_partitioning": "true",
}


def red_metrics(spans: DataFrame) -> DataFrame:
    """Server spans -> one row per (service, minute)."""
    server = spans.where(F.col("kind") == SPAN_KIND_SERVER)
    agg = server.groupBy("service", F.window("start_ts", "1 minute").alias("w")).agg(
        F.count("*").alias("request_count"),
        F.sum(F.when(F.col("status_code") == "ERROR", 1).otherwise(0)).alias("error_count"),
        F.percentile_approx("duration_ms", [0.5, 0.95, 0.99], 1000).alias("pct"),
    )
    return agg.select(
        "service",
        F.col("w.start").alias("minute"),
        "request_count",
        (F.col("request_count") / 60.0).alias("request_rate"),
        "error_count",
        (F.col("error_count") / F.col("request_count")).alias("error_rate"),
        F.col("pct")[0].alias("p50_ms"),
        F.col("pct")[1].alias("p95_ms"),
        F.col("pct")[2].alias("p99_ms"),
        F.current_timestamp().alias("computed_at"),
        F.date_format("w.start", "yyyy-MM-dd").alias("date"),
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--spans", default="s3a://silver/spans")
    p.add_argument("--output", default="s3a://gold/red_metrics")
    p.add_argument("--date", help="Recompute one day (yyyy-MM-dd)")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    spark = get_spark("gold_red_metrics")
    spans = spark.read.format("hudi").load(args.spans)
    if args.date:
        spans = spans.where(F.col("date") == args.date)
    # TODO: switch to Hudi incremental query (hoodie.datasource.query.type=incremental)
    # and recompute only the minutes touched since the last commit.
    red_metrics(spans).write.format("hudi").options(**HUDI_OPTIONS).mode("append").save(args.output)
    # TODO: gold.slo and gold.dependency_graph jobs build on this output.


if __name__ == "__main__":
    main()
