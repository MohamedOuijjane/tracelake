"""Helpers shared by tracelake DAGs."""

from __future__ import annotations

import logging
from datetime import timedelta

log = logging.getLogger(__name__)

DEFAULT_ARGS = {
    "owner": "tracelake",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

SPARK_SUBMIT = "docker compose exec -T spark-master bash /opt/tracelake/spark/submit.sh"


def todo(step: str, **_context) -> None:
    """Placeholder task body. Replace with the real implementation."""
    log.info("TODO: %s", step)
