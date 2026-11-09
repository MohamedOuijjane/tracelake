"""Hudi maintenance: compaction, clustering and cleaning for Silver and Gold tables."""

from __future__ import annotations

from datetime import datetime

from _common import DEFAULT_ARGS, todo

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator

MOR_TABLES = ["silver.spans", "silver.service_calls", "silver.metrics"]
ALL_TABLES = MOR_TABLES + ["gold.red_metrics", "gold.slo", "gold.dependency_graph"]

with DAG(
    dag_id="hudi_maintenance",
    description="Compact MoR tables, cluster small files, clean old file versions",
    schedule="0 2 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["hudi", "maintenance"],
) as dag:
    start = EmptyOperator(task_id="start")
    end = EmptyOperator(task_id="end")

    for table in MOR_TABLES:
        name = table.replace(".", "_")
        # TODO: run HoodieCompactor (schedule + execute) through spark-submit.
        compact = PythonOperator(
            task_id=f"compact_{name}",
            python_callable=todo,
            op_kwargs={"step": f"compact {table}"},
        )
        # TODO: run clustering to merge small files by service and start_ts.
        cluster = PythonOperator(
            task_id=f"cluster_{name}",
            python_callable=todo,
            op_kwargs={"step": f"cluster {table}"},
        )
        start >> compact >> cluster >> end

    for table in ALL_TABLES:
        name = table.replace(".", "_")
        # TODO: run HoodieCleaner, keep the last 24 commits.
        clean = PythonOperator(
            task_id=f"clean_{name}",
            python_callable=todo,
            op_kwargs={"step": f"clean {table}"},
        )
        start >> clean >> end
