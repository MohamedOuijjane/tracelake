"""Shared SparkSession builder with Hudi, Kafka and S3A (MinIO) settings.

Versions must stay aligned:
  Spark 3.5.x  ->  hudi-spark3.5-bundle_2.12, spark-sql-kafka-0-10_2.12:3.5.x, hadoop-aws 3.3.4
"""

from __future__ import annotations

import os
from collections.abc import Mapping

from pyspark.sql import SparkSession

SPARK_VERSION = "3.5.5"
SCALA_VERSION = "2.12"
HUDI_VERSION = "1.0.2"
HADOOP_AWS_VERSION = "3.3.4"

PACKAGES = [
    f"org.apache.hudi:hudi-spark3.5-bundle_{SCALA_VERSION}:{HUDI_VERSION}",
    f"org.apache.spark:spark-sql-kafka-0-10_{SCALA_VERSION}:{SPARK_VERSION}",
    f"org.apache.hadoop:hadoop-aws:{HADOOP_AWS_VERSION}",
]


def hudi_conf() -> dict[str, str]:
    """Settings Hudi needs on every session."""
    return {
        "spark.serializer": "org.apache.spark.serializer.KryoSerializer",
        "spark.sql.extensions": "org.apache.spark.sql.hudi.HoodieSparkSessionExtension",
        "spark.sql.catalog.spark_catalog": "org.apache.spark.sql.hudi.catalog.HoodieCatalog",
        "spark.kryo.registrator": "org.apache.spark.HoodieSparkKryoRegistrar",
    }


def s3a_conf(env: Mapping[str, str] | None = None) -> dict[str, str]:
    """S3A settings pointing at MinIO. Reads S3_ENDPOINT and MinIO credentials from env."""
    env = os.environ if env is None else env
    return {
        "spark.hadoop.fs.s3a.endpoint": env.get("S3_ENDPOINT", "http://minio:9000"),
        "spark.hadoop.fs.s3a.access.key": env.get("MINIO_ROOT_USER", ""),
        "spark.hadoop.fs.s3a.secret.key": env.get("MINIO_ROOT_PASSWORD", ""),
        "spark.hadoop.fs.s3a.path.style.access": "true",
        "spark.hadoop.fs.s3a.connection.ssl.enabled": "false",
        "spark.hadoop.fs.s3a.impl": "org.apache.hadoop.fs.s3a.S3AFileSystem",
        "spark.hadoop.fs.s3a.aws.credentials.provider": (
            "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider"
        ),
    }


def build_conf(
    *,
    with_hudi: bool = True,
    with_s3: bool = True,
    include_packages: bool = True,
    env: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Return the full config map. Pure function, easy to test."""
    conf: dict[str, str] = {
        "spark.sql.session.timeZone": "UTC",
        "spark.sql.shuffle.partitions": "8",
        "spark.jars.ivy": "/tmp/.ivy2",
    }
    if include_packages:
        conf["spark.jars.packages"] = ",".join(PACKAGES)
    if with_hudi:
        conf.update(hudi_conf())
    if with_s3:
        conf.update(s3a_conf(env))
    return conf


def get_spark(
    app_name: str,
    *,
    master: str | None = None,
    with_hudi: bool = True,
    with_s3: bool = True,
    include_packages: bool = True,
    extra_conf: Mapping[str, str] | None = None,
) -> SparkSession:
    """Build or reuse a SparkSession.

    When the job is launched with spark-submit (see submit.sh), packages are passed on the
    command line and spark.jars.packages here is ignored. When launched with plain python,
    this config downloads them.
    """
    builder = SparkSession.builder.appName(app_name)
    if master:
        builder = builder.master(master)
    conf = build_conf(with_hudi=with_hudi, with_s3=with_s3, include_packages=include_packages)
    if extra_conf:
        conf.update(extra_conf)
    for key, value in conf.items():
        builder = builder.config(key, value)
    return builder.getOrCreate()
