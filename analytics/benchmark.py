"""Separate-process, materialized pandas/Spark measurements on genuine saved records."""
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path

from .common import now, run_id, spark_session, write_json, writer_lock


def bytes_under(path):
    return sum(f.stat().st_size for f in Path(path).rglob('*') if f.is_file())


def worker(engine, input_path, output_path, result_path, master, partitions):
    from .features import spark_features, spark_aggregates, pandas_features, pandas_aggregates
    output = Path(output_path)
    output.mkdir(parents=True)
    session = None
    start = time.perf_counter()
    if engine == 'spark':
        session = spark_session(master, partitions)
    else:
        import pandas as pd
    startup = time.perf_counter() - start
    start = time.perf_counter()
    try:
        if engine == 'spark':
            data = session.read.parquet(str(input_path))
            features = spark_features(data).cache()
            features.write.parquet(str(output / 'features'))
            aggregates, rankings = spark_aggregates(features)
            aggregates.write.parquet(str(output / 'aggregates'))
            rankings.write.parquet(str(output / 'rankings'))
            rows = features.count()
            features.unpersist()
        else:
            data = pd.read_parquet(input_path)
            # Hive partition categories differ from Spark strings, not the records.
            for col in ['market', 'year']:
                if col in data:
                    data[col] = data[col].astype(str if col == 'market' else int)
            features = pandas_features(data)
            aggregates, rankings = pandas_aggregates(features)
            features.to_parquet(output / 'features.parquet', index=False)
            aggregates.to_parquet(output / 'aggregates.parquet', index=False)
            rankings.to_parquet(output / 'rankings.parquet', index=False)
            rows = len(features)
        elapsed = time.perf_counter() - start
        write_json(result_path, {'engine': engine, 'status': 'success', 'rows': rows,
                   'startup_seconds': startup, 'processing_seconds': elapsed,
                   'rows_per_second': rows / elapsed, 'output_bytes': bytes_under(output)})
    finally:
        if session:
            session.stop()


def benchmark(artifacts_root, repeats=3, master='local[2]', partitions=4, timeout=1800, max_rows=None):
    import importlib.metadata
    import psutil
    root = Path(artifacts_root).resolve()
    with writer_lock(root / '.benchmark.lock'):
        pointer = json.loads((root / 'current.json').read_text())
        source = root / 'runs' / pointer['run_id']
        manifest = json.loads((source / 'manifest.json').read_text())
        clean = Path(manifest['clean_path'])
        directory = root / 'benchmarks' / run_id()
        directory.mkdir(parents=True)
        source_rows = json.loads((source / 'overview.json').read_text())['records']
        measured_rows = source_rows
        if max_rows and max_rows < source_rows:
            # Prepare one deterministic, genuine subset outside all measured workers.
            preparation = spark_session(master, partitions)
            try:
                subset = preparation.read.parquet(str(clean)).orderBy('market', 'exchange', 'ticker', 'date').limit(max_rows)
                clean = directory / 'input'
                subset.write.parquet(str(clean))
                measured_rows = max_rows
            finally:
                preparation.stop()
        measurements = []
        for repeat in range(repeats):
            for engine in ('pandas', 'spark'):
                output = directory / f'{engine}-{repeat + 1}'
                result = directory / f'{engine}-{repeat + 1}.json'
                command = [sys.executable, '-m', 'analytics.cli', '_benchmark-worker', '--engine', engine,
                           '--input', str(clean), '--output', str(output), '--result', str(result),
                           '--master', master, '--partitions', str(partitions)]
                with (directory / f'{engine}-{repeat + 1}.log').open('w') as log:
                    begin, peak = time.perf_counter(), 0
                    child = subprocess.Popen(command, stdout=log, stderr=log)
                    timed_out = False
                    while child.poll() is None:
                        try:
                            parent = psutil.Process(child.pid)
                            processes = [parent] + parent.children(recursive=True)
                            rss = 0
                            for process in processes:
                                try:
                                    rss += process.memory_info().rss
                                except psutil.Error:
                                    pass
                            peak = max(peak, rss)
                            if time.perf_counter() - begin > timeout:
                                for process in reversed(processes):
                                    try:
                                        process.kill()
                                    except psutil.Error:
                                        pass
                                timed_out = True
                                break
                        except psutil.Error:
                            pass
                        time.sleep(0.1)
                    child.wait()
                    measurement = (json.loads(result.read_text()) if child.returncode == 0 and result.exists()
                                   else {'engine': engine, 'status': 'timeout' if timed_out else 'failed',
                                         'exit_code': child.returncode, 'log': str(log.name)})
                    measurement.update(repeat=repeat + 1, peak_process_tree_rss_bytes=peak,
                                       wall_seconds=time.perf_counter() - begin)
                    measurements.append(measurement)
                    write_json(directory / 'raw.json', measurements)
        summaries = []
        for engine in ('pandas', 'spark'):
            runs = [r for r in measurements if r['engine'] == engine and r['status'] == 'success']
            times = [r['processing_seconds'] for r in runs]
            summaries.append({'engine': engine, 'completed_runs': len(runs), 'requested_runs': repeats,
                              'median_seconds': statistics.median(times) if times else None,
                              'min_seconds': min(times) if times else None, 'max_seconds': max(times) if times else None,
                              'stdev_seconds': statistics.stdev(times) if len(times) > 1 else None,
                              'median_startup_seconds': statistics.median([r['startup_seconds'] for r in runs]) if runs else None,
                              'peak_process_tree_rss_bytes': max([r['peak_process_tree_rss_bytes'] for r in runs], default=None)})
        report = {'status': 'ready', 'run_id': pointer['run_id'], 'generated_at': now(),
                  'dataset_rows': measured_rows, 'source_dataset_rows': source_rows,
                  'input_bytes': bytes_under(clean), 'synthetic': False, 'summaries': summaries,
                  'measurements': measurements, 'environment': {'platform': platform.platform(),
                  'architecture': platform.machine(), 'logical_cpus': os.cpu_count(),
                  'ram_bytes': psutil.virtual_memory().total, 'python': platform.python_version(),
                  'versions': {p: importlib.metadata.version(p) for p in ['pandas', 'numpy', 'pyarrow', 'pyspark']},
                  'spark_master': master, 'shuffle_partitions': partitions},
                  'methodology': 'Each repeat in a fresh process. Engine import/startup reported separately. Processing includes Parquet read, identical features, date breadth/top-10 rankings, and output writes. Spark caches features only within that measured run. OS file cache is not cleared. An optional row-limited subset is ordered by stock/date and materialized once before measurements.',
                  'memory_method': 'Sum of worker and recursive child RSS sampled every 100 ms, including the JVM. Shared pages may be counted twice; short peaks may be missed.',
                  'limitations': ['Measured only on the genuine dataset available; no replicated or synthetic market coverage.',
                                  'Local Spark can be slower on small datasets. Separate runs share OS file caches.']}
        write_json(directory / 'report.json', report)
        write_json(root / 'benchmark-current.json', {'directory': directory.name, 'run_id': pointer['run_id']})
        return report
