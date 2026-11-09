# airflow

Airflow 2.10.5 with LocalExecutor and its own Postgres. DAGs are mounted read only from [dags/](dags). New DAGs start paused.

| DAG | Schedule | Purpose |
|---|---|---|
| `daily_performance_report` | 06:00 daily | RED and SLO summary for yesterday |
| `hudi_maintenance` | 02:00 daily | Compaction, clustering, cleaning |
| `model_retrain` | Monday 03:00 | Retrain the KMeans anomaly model |
| `data_quality` | hourly at :15 | Freshness, volume, key and completeness checks |

All tasks are placeholders that log a TODO. Each TODO comment says what the real task should do.

UI: http://localhost:8081, login from `.env`.

## Tests

```
pip install -r airflow/requirements.txt \
  --constraint https://raw.githubusercontent.com/apache/airflow/constraints-2.10.5/constraints-3.11.txt
pytest -q airflow/tests
```
