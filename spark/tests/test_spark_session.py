from common.spark_session import (
    HUDI_VERSION,
    PACKAGES,
    SPARK_VERSION,
    build_conf,
    s3a_conf,
)


def test_hudi_bundle_matches_spark_minor():
    spark_minor = ".".join(SPARK_VERSION.split(".")[:2])
    hudi = next(p for p in PACKAGES if "hudi" in p)
    assert f"hudi-spark{spark_minor}-bundle" in hudi
    assert hudi.endswith(HUDI_VERSION)


def test_kafka_package_matches_spark_version():
    kafka = next(p for p in PACKAGES if "spark-sql-kafka" in p)
    assert kafka.endswith(SPARK_VERSION)


def test_build_conf_includes_hudi_and_s3():
    env = {"S3_ENDPOINT": "http://minio:9000", "MINIO_ROOT_USER": "u", "MINIO_ROOT_PASSWORD": "p"}
    conf = build_conf(env=env)
    assert conf["spark.serializer"] == "org.apache.spark.serializer.KryoSerializer"
    assert "HoodieSparkSessionExtension" in conf["spark.sql.extensions"]
    assert conf["spark.hadoop.fs.s3a.endpoint"] == "http://minio:9000"
    assert conf["spark.hadoop.fs.s3a.access.key"] == "u"
    assert conf["spark.hadoop.fs.s3a.path.style.access"] == "true"
    assert conf["spark.sql.session.timeZone"] == "UTC"
    assert "spark.jars.packages" in conf


def test_build_conf_can_skip_parts():
    conf = build_conf(with_hudi=False, with_s3=False, include_packages=False)
    assert "spark.sql.extensions" not in conf
    assert not any(k.startswith("spark.hadoop.fs.s3a") for k in conf)
    assert "spark.jars.packages" not in conf


def test_s3a_defaults_when_env_empty():
    conf = s3a_conf({})
    assert conf["spark.hadoop.fs.s3a.endpoint"] == "http://minio:9000"


def test_local_session_runs_sql(spark):
    assert spark.conf.get("spark.sql.session.timeZone") == "UTC"
    assert spark.sql("SELECT 1 + 1 AS x").collect()[0].x == 2
