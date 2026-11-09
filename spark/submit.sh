#!/usr/bin/env bash
# Submit a job from spark/jobs to the local cluster.
# Usage (inside spark-master): bash /opt/tracelake/spark/submit.sh <job_name> [job args]
set -euo pipefail

JOB="${1:?usage: submit.sh <job_name> [args]}"
shift

# Keep in sync with spark/common/spark_session.py
PACKAGES="org.apache.hudi:hudi-spark3.5-bundle_2.12:1.0.2,org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.5,org.apache.hadoop:hadoop-aws:3.3.4"

exec /opt/spark/bin/spark-submit \
  --master "${SPARK_MASTER_URL:-spark://spark-master:7077}" \
  --packages "$PACKAGES" \
  --conf spark.jars.ivy=/tmp/.ivy2 \
  --conf spark.executor.memory=1g \
  --conf spark.driver.memory=768m \
  "/opt/tracelake/spark/jobs/${JOB}.py" "$@"
