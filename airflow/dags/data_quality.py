"""Hourly data quality checks across Bronze, Silver and Gold."""

from __future__ import annotations

from datetime import datetime

from _common import DEFAULT_ARGS, todo

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator

CHECKS = {
    "bronze_freshness": "latest Bronze partition is less than 15 minutes old",
    "bronze_volume": "row count in the last hour is within 3 std of the 7 day mean",
    "silver_keys_unique": "no duplicate (trace_id, span_id) in silver.spans",
    "silver_required_fields": "trace_id, span_id, service, start_ts are never null",
    "silver_compaction_lag": "pending MoR log files below threshold",
    "gold_completeness": "every active service has a row for each minute of the last hour",
    "kafka_consumer_lag": "bronze_ingest lag on otel.traces below 100k",
}

with DAG(
    dag_id="data_quality",
    description="Freshness, volume, uniqueness and completeness checks",
    schedule="15 * * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["quality"],
) as dag:
    start = EmptyOperator(task_id="start")

    # TODO: on failure, publish a message to the alerts topic and fail the task.
    report = PythonOperator(
        task_id="publish_results",
        python_callable=todo,
        op_kwargs={"step": "write check results to s3://gold/quality/ and alerts topic"},
        trigger_rule="all_done",
    )

    for check_id, description in CHECKS.items():
        # TODO: implement each check as a Trino query or a small Spark job.
        task = PythonOperator(
            task_id=check_id,
            python_callable=todo,
            op_kwargs={"step": description},
        )
        start >> task >> report
