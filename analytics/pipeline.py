"""Spark validation, features, bounded exports, and atomic snapshot publication."""
import hashlib
import json
import time
from pathlib import Path

from .common import COLUMNS, KEYS, MARKETS, now, run_id, spark_session, write_json, writer_lock
from .features import spark_features


def raw_files(data_root):
    files, manifests = [], []
    for path in sorted((Path(data_root) / 'raw').glob('*/manifest.json')):
        manifest = json.loads(path.read_text())
        manifests.append(manifest)
        names = manifest.get('files', []) + [r['file'] for r in manifest.get('downloads', [])
                                           if r['status'] in ('success', 'partial')]
        files.extend(str(path.parent / name) for name in names if (path.parent / name).is_file())
    return sorted(set(files)), manifests


def clean_data(raw):
    from pyspark.sql import functions as F, Window
    data = raw
    for column in ('ticker', 'market', 'exchange', 'currency'):
        data = data.withColumn(column, F.upper(F.trim(F.col(column))))
    data = data.withColumn('_hash', F.sha2(F.to_json(F.struct(*COLUMNS)), 256))
    data = data.withColumn('_date_text', F.col('date')).withColumn('_adj_text', F.col('adj_close'))
    data = data.withColumn('date', F.expr('try_cast(date as date)'))
    data = data.withColumn('fetched_at', F.expr('try_cast(fetched_at as timestamp)'))
    for column in ['open', 'high', 'low', 'close', 'adj_close', 'volume']:
        data = data.withColumn(column, F.expr(f'try_cast({column} as double)'))
    def bad_number(column):
        return F.col(column).isNull() | F.isnan(column) | (F.abs(F.col(column)) == float('inf'))
    tests = [
        ('invalid_identifier', F.col('ticker').isNull() | ~F.col('ticker').rlike(r'^[A-Z0-9^][A-Z0-9.^=-]{0,19}$')
         | F.col('exchange').isNull() | ~F.col('exchange').rlike(r'^[A-Z0-9_ -]{1,30}$')),
        ('invalid_market_currency', ~F.col('market').isin(*MARKETS) | F.col('market').isNull()
         | F.col('currency').isNull() | ~((F.col('market') == 'US') & (F.col('currency') == 'USD')
                 | (F.col('market').isin('NSE', 'BSE')) & (F.col('currency') == 'INR'))),
        ('invalid_date', F.col('date').isNull() | ~F.col('_date_text').rlike(r'^\d{4}-\d{2}-\d{2}$')
         | (F.col('date') > F.current_date())),
        ('invalid_provenance', F.col('fetched_at').isNull() | F.col('source').isNull() | (F.trim('source') == '')),
        ('invalid_price', bad_number('open') | bad_number('high') | bad_number('low') | bad_number('close')
         | (F.least('open', 'high', 'low', 'close') <= 0)),
        ('invalid_adjusted_close', F.col('_adj_text').isNotNull() & ~F.lower(F.trim('_adj_text')).isin('', 'nan', 'null', 'none')
         & (bad_number('adj_close') | (F.col('adj_close') <= 0))),
        ('invalid_volume', bad_number('volume') | (F.col('volume') < 0)
         | (F.col('volume') != F.floor('volume'))),
        ('inconsistent_ohlc', (F.col('high') < F.greatest('open', 'close', 'low'))
         | (F.col('low') > F.least('open', 'close', 'high'))),
    ]
    data = data.withColumn('rejection_reasons', F.concat_ws('|', *[
        F.when(F.coalesce(condition, F.lit(False)), F.lit(name)) for name, condition in tests]))
    # Null/NaN adjusted close stays unavailable: never substitute unadjusted close.
    data = data.withColumn('adj_close', F.when(bad_number('adj_close'), F.lit(None)).otherwise(F.col('adj_close')))
    rejected = data.filter(F.col('rejection_reasons') != '')
    valid = data.filter(F.col('rejection_reasons') == '')
    latest = Window.partitionBy(*KEYS, 'date').orderBy(F.desc('fetched_at'), F.desc('_hash'))
    clean = (valid.withColumn('_rank', F.row_number().over(latest)).filter('_rank = 1')
             .select(*COLUMNS).withColumn('year', F.year('date')))
    return clean, rejected, valid


def _records(frame):
    """Streaming JSON rows; does not collect the complete dataset on the driver."""
    for row in frame.toJSON().toLocalIterator():
        yield json.loads(row)


def export_dashboard(features, directory, max_sessions=3000):
    from pyspark.sql import functions as F, Window
    identity = Window.partitionBy(*KEYS).orderBy(F.desc('date'))
    bounded = features.withColumn('_recent', F.row_number().over(identity)).filter(F.col('_recent') <= max_sessions)
    series_fields = ['date', 'open', 'high', 'low', 'close', 'adj_close', 'volume', 'daily_return',
                     'sma_20', 'sma_50', 'volatility_20', 'volume_ratio', 'volume_anomaly',
                     'gap_sessions', 'calendar_gap_days']
    stocks, current, buffer, meta = [], None, [], None
    def flush():
        if meta is not None:
            key = hashlib.sha256(('|'.join(current)).encode()).hexdigest()[:24]
            filename = f'stocks/{key}.json'
            write_json(directory / filename, {**meta, 'data': buffer, 'retention_sessions': max_sessions})
            stocks.append({**meta, 'file': filename, 'sessions': len(buffer),
                           'start': buffer[0]['date'], 'end': buffer[-1]['date']})
    for row in _records(bounded.orderBy(*KEYS, 'date').select(*KEYS, 'currency', *series_fields)):
        key = tuple(row[k] for k in KEYS)
        if key != current:
            flush()
            current, buffer = key, []
            meta = {k: row[k] for k in KEYS + ['currency']}
        buffer.append({k: row.get(k) for k in series_fields})
    flush()
    # Keep the API's market/ticker lookup unambiguous across exchanges.
    identities = [(s['market'], s['ticker']) for s in stocks]
    if len(set(identities)) != len(identities):
        raise ValueError('A market/ticker occurs on multiple exchanges; use distinct provider-qualified tickers')
    day_window = Window.partitionBy('market').orderBy(F.desc('date'))
    recent_dates = (features.select('market', 'date').distinct().withColumn('_day', F.row_number().over(day_window))
                    .filter(F.col('_day') <= max_sessions).drop('_day'))
    recent = features.join(recent_dates, ['market', 'date'])
    breadth = recent.groupBy('market', 'date').agg(
        F.count('*').alias('stocks'),
        *[F.sum(F.when(condition, 1).otherwise(0)).alias(label) for label, condition in [
            ('advancing', F.col('daily_return') > 0), ('declining', F.col('daily_return') < 0),
            ('unchanged', F.col('daily_return') == 0), ('unavailable', F.col('daily_return').isNull())]])
    by_day = {}
    for row in _records(breadth.orderBy('market', 'date')):
        market, day = row.pop('market'), row.pop('date')
        by_day[(market, day)] = {'market': market, 'date': day, 'breadth': row,
                                'gainers': [], 'losers': [], 'volatile': [], 'anomalies': []}
    ranked_fields = KEYS + ['currency', 'date', 'close', 'adj_close', 'daily_return', 'volatility_20', 'volume_ratio']
    # Only the bounded top ten per date/category leaves Spark.
    ranked = None
    for category, metric, descending, condition in [
        ('gainers', 'daily_return', True, F.col('daily_return') > 0),
        ('losers', 'daily_return', False, F.col('daily_return') < 0),
        ('volatile', 'volatility_20', True, F.col('volatility_20').isNotNull()),
        ('anomalies', 'volume_ratio', True, F.col('volume_anomaly') == True),
    ]:
        order = F.desc(metric) if descending else F.asc(metric)
        window = Window.partitionBy('market', 'date').orderBy(order, *KEYS)
        top = (recent.filter(condition).withColumn('_rank', F.row_number().over(window))
               .filter('_rank <= 10').select(*ranked_fields, '_rank').withColumn('category', F.lit(category)))
        ranked = top if ranked is None else ranked.unionByName(top)
    for row in _records(ranked.orderBy('market', 'date', 'category', '_rank')):
        category = row.pop('category')
        row.pop('_rank')
        by_day[(row['market'], row['date'])][category].append(row)
    markets = {}
    for (market, day), snapshot in by_day.items():
        write_json(directory / 'rankings' / market / f'{day}.json', snapshot)
        markets.setdefault(market, {'currency': MARKETS[market], 'dates': []})['dates'].append(day)
    return stocks, markets


def process(data_root, artifacts_root, master='local[2]', partitions=4, anomaly_threshold=2.0):
    data_root, artifacts_root = Path(data_root).resolve(), Path(artifacts_root).resolve()
    with writer_lock(artifacts_root / '.publish.lock'):
        identifier, started = run_id(), time.perf_counter()
        directory = artifacts_root / 'runs' / identifier
        directory.mkdir(parents=True)
        state = {'status': 'running', 'run_id': identifier, 'started_at': now()}
        write_json(artifacts_root / 'status.json', state)
        spark = None
        try:
            files, manifests = raw_files(data_root)
            if not files:
                raise ValueError('No ingested data. Run ingest or import-csv first.')
            spark = spark_session(master, partitions)
            raw = spark.read.option('header', True).schema(', '.join(f'{c} STRING' for c in COLUMNS)).csv(files).cache()
            clean, rejected, valid = clean_data(raw)
            clean, rejected = clean.cache(), rejected.cache()
            input_count, rejected_count, valid_count, accepted = raw.count(), rejected.count(), valid.count(), clean.count()
            if not accepted:
                raise ValueError(f'All {input_count} input rows were rejected; previous snapshot preserved')
            rejected.write.mode('error').parquet(str(data_root / 'quarantine' / identifier))
            clean_path = data_root / 'clean' / identifier
            clean.repartition(partitions, 'market', 'year').write.partitionBy('market', 'year').parquet(str(clean_path))
            features = spark_features(clean, anomaly_threshold).cache()
            feature_path = data_root / 'features' / identifier
            features.repartition(partitions, 'market', 'year').write.partitionBy('market', 'year').parquet(str(feature_path))
            from pyspark.sql import functions as F
            reasons = {r['reason']: r['count'] for r in rejected.select(
                F.explode(F.split('rejection_reasons', r'\|')).alias('reason')).groupBy('reason').count().collect()}
            coverage = clean.agg(F.min('date').alias('start'), F.max('date').alias('end')).first().asDict()
            diagnostics = features.agg(
                F.sum(F.when(F.col('adj_close').isNull(), 1).otherwise(0)).alias('missing_adjusted_close'),
                F.sum(F.when(F.col('volume') == 0, 1).otherwise(0)).alias('zero_volume'),
                F.sum(F.when(F.col('gap_sessions') > 0, 1).otherwise(0)).alias('observed_session_gaps'),
                F.sum(F.when(F.col('calendar_gap_days') > 7, 1).otherwise(0)).alias('long_calendar_gaps')).first().asDict()
            stocks, markets = export_dashboard(features, directory)
            quality = {'input_rows': input_count, 'accepted_rows': accepted,
                       'duplicate_rows': valid_count - accepted, 'rejected_rows': rejected_count,
                       'rejection_reasons': reasons, **diagnostics,
                       'calendar_method': 'Observed exchange-session union; gaps over 7 calendar days also suppressed. Official holiday calendar not verified.'}
            generated = now()
            overview = {'status': 'ready', 'run_id': identifier, 'generated_at': generated,
                        'records': accepted, 'stocks_count': len(stocks), 'date_range': coverage,
                        'latest_session': str(coverage['end']), 'quality': quality, 'markets': markets,
                        'stocks': stocks, 'execution': {'engine': 'Apache Spark', 'mode': master,
                        'spark_version': spark.version, 'shuffle_partitions': partitions,
                        'runtime_seconds': round(time.perf_counter() - started, 3)},
                        'methodology': {'returns': 'Adjusted close; consecutive observed exchange sessions only',
                        'moving_averages': '20 / 50 sessions; complete windows',
                        'volatility': '20-session sample standard deviation; not annualized',
                        'volume_ratio': 'Current volume / previous 20 sessions, excluding current',
                        'anomaly_threshold': anomaly_threshold, 'retention_sessions': 3000},
                        'sources': sorted({m.get('source', 'unknown') for m in manifests}),
                        'limitations': ['Historical daily batch data, not a live feed.',
                        'A curated present-day universe has survivorship bias; no historical membership claim.',
                        'Local Spark worker threads run on one machine, not a distributed cluster.',
                        'Missing adjusted close and uncertain session gaps suppress affected return metrics.']}
            write_json(directory / 'overview.json', overview)
            write_json(directory / 'quality.json', quality)
            manifest = {'schema_version': 1, 'run_id': identifier, 'generated_at': generated,
                        'clean_path': str(clean_path), 'features_path': str(feature_path),
                        'input_bytes': sum(Path(p).stat().st_size for p in files),
                        'input_manifests': manifests, 'status': 'complete'}
            write_json(directory / 'manifest.json', manifest)
            validate_snapshot(directory)
            write_json(artifacts_root / 'current.json', {'run_id': identifier, 'schema_version': 1})
            write_json(artifacts_root / 'status.json', {**state, 'status': 'complete', 'completed_at': now()})
            return overview
        except Exception as exc:
            write_json(artifacts_root / 'status.json', {**state, 'status': 'failed', 'failed_at': now(), 'error': str(exc)})
            raise
        finally:
            if spark:
                spark.stop()


def validate_snapshot(directory):
    overview = json.loads((directory / 'overview.json').read_text())
    quality = overview['quality']
    if quality['input_rows'] != quality['accepted_rows'] + quality['duplicate_rows'] + quality['rejected_rows']:
        raise ValueError('Quality counts do not reconcile')
    if not overview['markets'] or not overview['stocks']:
        raise ValueError('Snapshot has no dashboard coverage')
    for stock in overview['stocks']:
        data = json.loads((directory / stock['file']).read_text())['data']
        if not data or len(data) > 3000:
            raise ValueError('Invalid stock series export')
    for market, metadata in overview['markets'].items():
        for day in metadata['dates']:
            row = json.loads((directory / 'rankings' / market / f'{day}.json').read_text())
            if sum(row['breadth'][k] for k in ['advancing', 'declining', 'unchanged', 'unavailable']) != row['breadth']['stocks']:
                raise ValueError('Breadth does not reconcile')
