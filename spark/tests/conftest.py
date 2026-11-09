import pytest

from common.spark_session import get_spark


@pytest.fixture(scope="session")
def spark():
    session = get_spark(
        "tracelake-tests",
        master="local[1]",
        with_hudi=False,
        with_s3=False,
        include_packages=False,
        extra_conf={"spark.ui.enabled": "false"},
    )
    yield session
    session.stop()
