"""Silver spans: Bronze OTLP JSON -> one row per span -> Hudi MoR upsert.

Skeleton. Parsing and the Hudi write work; incremental reads are a TODO.

Run: bash /opt/tracelake/spark/submit.sh silver_spans --date 2026-11-09
"""

from __future__ import annotations

import argparse

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql import types as T

from common.spark_session import get_spark

ATTR = T.StructType(
    [
        T.StructField("key", T.StringType()),
        T.StructField(
            "value",
            T.StructType(
                [
                    T.StructField("stringValue", T.StringType()),
                    T.StructField("intValue", T.StringType()),
                    T.StructField("doubleValue", T.DoubleType()),
                    T.StructField("boolValue", T.BooleanType()),
                ]
            ),
        ),
    ]
)

SPAN = T.StructType(
    [
        T.StructField("traceId", T.StringType()),
        T.StructField("spanId", T.StringType()),
        T.StructField("parentSpanId", T.StringType()),
        T.StructField("name", T.StringType()),
        T.StructField("kind", T.IntegerType()),
        T.StructField("startTimeUnixNano", T.StringType()),
        T.StructField("endTimeUnixNano", T.StringType()),
        T.StructField("attributes", T.ArrayType(ATTR)),
        T.StructField("status", T.StructType([T.StructField("code", T.IntegerType())])),
    ]
)

OTLP_TRACES = T.StructType(
    [
        T.StructField(
            "resourceSpans",
            T.ArrayType(
                T.StructType(
                    [
                        T.StructField(
                            "resource",
                            T.StructType([T.StructField("attributes", T.ArrayType(ATTR))]),
                        ),
                        T.StructField(
                            "scopeSpans",
                            T.ArrayType(T.StructType([T.StructField("spans", T.ArrayType(SPAN))])),
                        ),
                    ]
                )
            ),
        )
    ]
)

STATUS_NAMES = {0: "UNSET", 1: "OK", 2: "ERROR"}

HUDI_OPTIONS = {
    "hoodie.table.name": "spans",
    "hoodie.datasource.write.table.type": "MERGE_ON_READ",
    "hoodie.datasource.write.operation": "upsert",
    "hoodie.datasource.write.recordkey.field": "trace_id,span_id",
    "hoodie.datasource.write.precombine.field": "end_ts",
    "hoodie.datasource.write.partitionpath.field": "date",
    "hoodie.datasource.write.keygenerator.class": "org.apache.hudi.keygen.ComplexKeyGenerator",
    "hoodie.datasource.write.hive_style_partitioning": "true",
    # Compaction runs from Airflow (hudi_maintenance DAG), not inline.
    "hoodie.compact.inline": "false",
}


def attr_value_expr(a: F.Column) -> F.Column:
    """OTLP AnyValue -> string."""
    v = a.value
    return F.coalesce(
        v.stringValue, v.intValue, v.doubleValue.cast("string"), v.boolValue.cast("string")
    )


def status_name(code: F.Column) -> F.Column:
    """OTLP status code (0, 1, 2) -> contract enum name."""
    expr = F.lit("UNSET")
    for value, name in STATUS_NAMES.items():
        expr = F.when(code == value, name).otherwise(expr)
    return expr


def flatten_spans(bronze: DataFrame) -> DataFrame:
    """Bronze rows with an OTLP JSON payload -> rows matching contracts/span.avsc."""
    parsed = bronze.select(F.from_json("payload", OTLP_TRACES).alias("otlp"))
    rs = parsed.select(F.explode("otlp.resourceSpans").alias("rs"))
    rs = rs.withColumn(
        "service",
        F.expr("filter(rs.resource.attributes, a -> a.key = 'service.name')[0].value.stringValue"),
    )
    spans = rs.select("service", F.explode("rs.scopeSpans").alias("ss")).select(
        "service", F.explode("ss.spans").alias("s")
    )
    start_ns = F.col("s.startTimeUnixNano").cast("decimal(20,0)")
    end_ns = F.col("s.endTimeUnixNano").cast("decimal(20,0)")
    return spans.select(
        F.col("s.traceId").alias("trace_id"),
        F.col("s.spanId").alias("span_id"),
        F.when(F.col("s.parentSpanId") == "", None)
        .otherwise(F.col("s.parentSpanId"))
        .alias("parent_span_id"),
        F.coalesce("service", F.lit("unknown")).alias("service"),
        F.col("s.name").alias("operation"),
        F.col("s.kind").alias("kind"),
        F.timestamp_micros((start_ns / 1000).cast("long")).alias("start_ts"),
        F.timestamp_micros((end_ns / 1000).cast("long")).alias("end_ts"),
        ((end_ns - start_ns) / 1e6).cast("double").alias("duration_ms"),
        status_name(F.col("s.status.code")).alias("status_code"),
        F.map_from_entries(
            F.transform("s.attributes", lambda a: F.struct(a.key, attr_value_expr(a)))
        ).alias("attributes"),
    ).withColumn("date", F.date_format("start_ts", "yyyy-MM-dd"))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bronze", default="s3a://bronze/otel_traces")
    p.add_argument("--output", default="s3a://silver/spans")
    p.add_argument("--date", help="Process one Bronze date partition (yyyy-MM-dd)")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    spark = get_spark("silver_spans")
    bronze = spark.read.parquet(args.bronze)
    if args.date:
        bronze = bronze.where(F.col("date") == args.date)
    # TODO: read only new Bronze files (track last processed kafka offsets or file times).
    # TODO: send rows that fail to parse to the dlq topic.
    spans = flatten_spans(bronze).dropDuplicates(["trace_id", "span_id"])
    spans.write.format("hudi").options(**HUDI_OPTIONS).mode("append").save(args.output)
    # TODO: derive silver.service_calls from parent/child pairs across services.


if __name__ == "__main__":
    main()
