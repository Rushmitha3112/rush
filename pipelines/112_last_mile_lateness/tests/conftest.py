import os
import time

import pytest
from pyspark.sql import SparkSession

# collect() turns timestamps into naive datetimes in the *driver's* local zone.
# Pin it so the tests don't depend on the laptop's timezone.
os.environ["TZ"] = "UTC"
time.tzset()


@pytest.fixture(scope="session")
def spark():
    s = (SparkSession.builder.master("local[2]").appName("tests")
         .config("spark.sql.shuffle.partitions", "2")
         .config("spark.sql.session.timeZone", "UTC")
         .config("spark.ui.enabled", "false")
         .getOrCreate())
    s.sparkContext.setLogLevel("ERROR")
    yield s
    s.stop()


@pytest.fixture(scope="session")
def pg_dsn():
    dsn = os.getenv("PG_DSN")
    if not dsn:
        pytest.skip("PG_DSN not set, skipping warehouse tests")
    return dsn
