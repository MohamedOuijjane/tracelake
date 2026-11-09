"""Daily performance report: yesterday's RED metrics and SLOs per service."""

from __future__ import annotations

from datetime import datetime

from _common import DEFAULT_ARGS, todo

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator

with DAG(
    dag_id="daily_performance_report",
    description="Summarise yesterday's RED metrics and SLO burn per service",
    schedule="0 6 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["gold", "report"],
) as dag:
    start = EmptyOperator(task_id="start")

    # TODO: run gold_red_metrics.py for {{ ds }} on the Spark cluster.
    refresh_red = PythonOperator(
        task_id="refresh_red_metrics",
        python_callable=todo,
        op_kwargs={"step": "spark-submit gold_red_metrics --date {{ ds }}"},
    )

    # TODO: compute gold.slo for the 24 h and 30 d windows.
    refresh_slo = PythonOperator(
        task_id="refresh_slo",
        python_callable=todo,
        op_kwargs={"step": "spark-submit gold_slo --date {{ ds }}"},
    )

    # TODO: query Trino for top 5 slowest services and biggest p99 regressions.
    build_report = PythonOperator(
        task_id="build_report",
        python_callable=todo,
        op_kwargs={"step": "query Trino and render the report"},
    )

    # TODO: post the report (Slack webhook or email) and store it in s3://gold/reports/.
    publish = PythonOperator(
        task_id="publish_report",
        python_callable=todo,
        op_kwargs={"step": "publish report"},
    )

    end = EmptyOperator(task_id="end")

    start >> [refresh_red, refresh_slo] >> build_report >> publish >> end
