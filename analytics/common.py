"""Small shared helpers; importing these never starts Spark."""
import json
import os
import re
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COLUMNS = ['ticker', 'market', 'exchange', 'currency', 'date', 'open', 'high',
           'low', 'close', 'adj_close', 'volume', 'source', 'fetched_at']
KEYS = ['market', 'exchange', 'ticker']
SYMBOL = re.compile(r'^[A-Z0-9^][A-Z0-9.^=-]{0,19}$')
MARKETS = {'US': 'USD', 'NSE': 'INR', 'BSE': 'INR'}


def now():
    return datetime.now(timezone.utc).isoformat()


def run_id():
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:8]


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with temp.open('w') as f:
            json.dump(value, f, indent=2, allow_nan=False, default=str)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


@contextmanager
def writer_lock(path):
    """OS releases flock after a crash; concurrent publishers fail explicitly."""
    import fcntl
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError(f'Another writer is using {path.parent}') from None
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def spark_session(master='local[2]', partitions=4):
    import sys
    os.environ.setdefault('SPARK_LOCAL_IP', '127.0.0.1')
    os.environ['PYSPARK_PYTHON'] = sys.executable
    from pyspark.sql import SparkSession
    session = (SparkSession.builder.master(master).appName('StockAI historical analytics')
               .config('spark.driver.host', '127.0.0.1')
               .config('spark.driver.bindAddress', '127.0.0.1')
               .config('spark.ui.enabled', 'false')
               .config('spark.sql.shuffle.partitions', str(partitions))
               .config('spark.sql.session.timeZone', 'UTC')
               .config('spark.sql.ansi.enabled', 'false')
               .getOrCreate())
    session.sparkContext.setLogLevel('ERROR')
    return session
