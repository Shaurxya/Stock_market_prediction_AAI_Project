"""Immutable, resumable Yahoo batches and canonical CSV import."""
import csv
import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path

from .common import COLUMNS, MARKETS, SYMBOL, now, run_id, write_json, writer_lock


def load_universe(path, limit=None):
    with Path(path).open(newline='') as f:
        rows = list(csv.DictReader(f))
    seen = set()
    for row in rows:
        identity = (row['market'], row['ticker'])
        if (not SYMBOL.fullmatch(row['ticker']) or row['market'] not in MARKETS
                or row['currency'] != MARKETS[row['market']] or not row['exchange']):
            raise ValueError(f'Invalid universe entry: {row}')
        if identity in seen:
            raise ValueError(f'Duplicate universe identity: {identity}')
        seen.add(identity)
    return rows[:limit] if limit else rows


def import_csv(path, data_root):
    """Hash-based idempotence. Bad values remain raw for Spark quarantine."""
    path, raw = Path(path), Path(data_root) / 'raw'
    with path.open('rb') as file:
        digest = hashlib.file_digest(file, 'sha256').hexdigest()
    with writer_lock(raw / '.ingest.lock'):
        destination = raw / ('csv-' + digest)
        if (destination / 'manifest.json').exists():
            return json.loads((destination / 'manifest.json').read_text())
        with path.open(newline='') as f:
            reader = csv.DictReader(f)
            missing = set(COLUMNS) - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f'CSV missing canonical columns: {sorted(missing)}')
            destination.mkdir(parents=True, exist_ok=True)
            count = 0
            with (destination / 'data.csv').open('w', newline='') as out:
                writer = csv.DictWriter(out, fieldnames=COLUMNS, extrasaction='ignore')
                writer.writeheader()
                for row in reader:
                    writer.writerow(row)
                    count += 1
        manifest = {'batch_id': destination.name, 'source': 'local_csv', 'input': str(path.resolve()),
                    'sha256': digest, 'rows': count, 'completed_at': now(), 'status': 'success',
                    'files': ['data.csv']}
        write_json(destination / 'manifest.json', manifest)
        return manifest


def _download(stock, start, end, destination, retries):
    import yfinance as yf
    result = {**stock, 'requested_start': start, 'requested_end_exclusive': end}
    error = None
    for attempt in range(retries):
        try:
            frame = yf.Ticker(stock['ticker']).history(
                start=start, end=end, auto_adjust=False, actions=False,
                timeout=25, raise_errors=True)
            if frame is None or frame.empty:
                result.update(status='empty', rows=0, attempts=attempt + 1)
                return result
            fetched = now()
            filename = hashlib.sha256((stock['market'] + ':' + stock['ticker']).encode()).hexdigest()[:20] + '.csv'
            with (destination / filename).open('w', newline='') as out:
                writer = csv.DictWriter(out, fieldnames=COLUMNS)
                writer.writeheader()
                for session, row in frame.iterrows():
                    writer.writerow({**{k: stock[k] for k in ('ticker', 'market', 'exchange', 'currency')},
                                     'date': session.date().isoformat(),
                                     **{name: row.get(provider, '') for name, provider in
                                        [('open', 'Open'), ('high', 'High'), ('low', 'Low'), ('close', 'Close'),
                                         ('adj_close', 'Adj Close'), ('volume', 'Volume')]},
                                     'source': 'yahoo_finance', 'fetched_at': fetched})
            first, last = frame.index[0].date(), frame.index[-1].date()
            partial = (first > date.fromisoformat(start) + timedelta(days=7)
                       or last < date.fromisoformat(end) - timedelta(days=7)
                       or 'Adj Close' not in frame or frame['Adj Close'].isna().any())
            result.update(status='partial' if partial else 'success', rows=len(frame), file=filename,
                          actual_start=str(first), actual_end=str(last), fetched_at=fetched,
                          attempts=attempt + 1)
            return result
        except Exception as exc:
            error = str(exc)
            if attempt + 1 < retries:
                time.sleep(min(16, 2 ** attempt))
    result.update(status='failed', rows=0, error=error, attempts=retries)
    return result


def ingest(universe, data_root, start, end, workers=2, retries=3, refresh=False, incremental=False):
    if date.fromisoformat(start) >= date.fromisoformat(end):
        raise ValueError('start must precede exclusive end')
    raw = Path(data_root) / 'raw'
    with writer_lock(raw / '.ingest.lock'):
        previous = {}
        for file in sorted(raw.glob('*/manifest.json')):
            manifest = json.loads(file.read_text())
            for item in manifest.get('downloads', []):
                if item['status'] in ('success', 'partial') and (file.parent / item.get('file', '')).is_file():
                    key = (item['market'], item['ticker'])
                    if item.get('fetched_at', '') > previous.get(key, {}).get('fetched_at', ''):
                        previous[key] = item
        batch = raw / run_id()
        batch.mkdir(parents=True)
        results, tasks = [], {}
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for stock in universe:
                old = previous.get((stock['market'], stock['ticker']))
                effective_start = start
                if old and not refresh:
                    coverage_start = old.get('coverage_start', old['requested_start'])
                    if (not incremental and coverage_start <= start
                            and old['requested_end_exclusive'] >= end and old['status'] == 'success'):
                        results.append({**stock, 'status': 'cached', 'rows': old['rows']})
                        continue
                    if incremental and coverage_start <= start:
                        effective_start = max(start, str(date.fromisoformat(old['actual_end']) - timedelta(days=10)))
                task = pool.submit(_download, stock, effective_start, end, batch, retries)
                tasks[task] = old if incremental and not refresh else None
            for task in as_completed(tasks):
                result = task.result()
                if result['status'] in ('success', 'partial'):
                    old = tasks[task]
                    result['coverage_start'] = min(result['requested_start'],
                        old.get('coverage_start', old['requested_start']) if old else result['requested_start'])
                    if old and old['status'] == 'partial':
                        result['status'] = 'partial'
                results.append(result)
                # A crash resumes completed symbols without repeating their download.
                write_json(batch / 'manifest.json', {'batch_id': batch.name, 'source': 'yahoo_finance',
                           'status': 'in_progress', 'downloads': sorted(results, key=lambda r: r['ticker'])})
        manifest = {'batch_id': batch.name, 'source': 'yahoo_finance', 'completed_at': now(),
                    'status': 'complete', 'adjustment': 'auto_adjust=False',
                    'incremental': incremental, 'downloads': sorted(results, key=lambda r: r['ticker'])}
        write_json(batch / 'manifest.json', manifest)
        return manifest
