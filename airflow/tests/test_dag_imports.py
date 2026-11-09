"""Every DAG in airflow/dags must import cleanly and follow basic rules."""

import sys
from pathlib import Path

import pytest

from airflow.models import DagBag

DAGS_DIR = Path(__file__).resolve().parents[1] / "dags"
# The scheduler puts the dags folder on sys.path, so DAGs can import _common. Do the same here.
sys.path.insert(0, str(DAGS_DIR))
EXPECTED = {"daily_performance_report", "hudi_maintenance", "model_retrain", "data_quality"}


@pytest.fixture(scope="module")
def dagbag():
    return DagBag(dag_folder=str(DAGS_DIR), include_examples=False)


def test_no_import_errors(dagbag):
    assert dagbag.import_errors == {}


def test_expected_dags_present(dagbag):
    assert EXPECTED <= set(dagbag.dag_ids)


@pytest.mark.parametrize("dag_id", sorted(EXPECTED))
def test_dag_basics(dagbag, dag_id):
    dag = dagbag.get_dag(dag_id)
    assert dag.catchup is False
    assert dag.tags, f"{dag_id} has no tags"
    assert len(dag.tasks) > 0
