"""Weekly retrain of the KMeans anomaly model on recent RED metrics."""

from __future__ import annotations

from datetime import datetime

from _common import DEFAULT_ARGS, todo

from airflow import DAG
from airflow.operators.python import PythonOperator

with DAG(
    dag_id="model_retrain",
    description="Retrain KMeans on the last 7 days of gold.red_metrics",
    schedule="0 3 * * 1",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["ml", "anomaly"],
) as dag:
    # TODO: check that gold.red_metrics has at least 7 days of data for each service.
    check_data = PythonOperator(
        task_id="check_training_data",
        python_callable=todo,
        op_kwargs={"step": "count rows per service in gold.red_metrics"},
    )

    # TODO: spark-submit anomaly_detection with a --train-only flag, write to a dated path.
    train = PythonOperator(
        task_id="train_model",
        python_callable=todo,
        op_kwargs={"step": "train KMeans and save to s3a://gold/models/red_kmeans/{{ ds }}"},
    )

    # TODO: compare silhouette score with the current model, keep the better one.
    evaluate = PythonOperator(
        task_id="evaluate_model",
        python_callable=todo,
        op_kwargs={"step": "evaluate new model against current"},
    )

    # TODO: update the "current" pointer used by the scoring job.
    promote = PythonOperator(
        task_id="promote_model",
        python_callable=todo,
        op_kwargs={"step": "promote model"},
    )

    check_data >> train >> evaluate >> promote
