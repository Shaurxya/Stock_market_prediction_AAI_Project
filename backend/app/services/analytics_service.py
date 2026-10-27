"""Serve only completed, bounded JSON artifacts. No analytics/ML imports required."""
import json
import os
import re
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

from fastapi import HTTPException

DEFAULT_ROOT = Path(__file__).resolve().parents[3] / 'artifacts' / 'analytics'
RUN_ID = re.compile(r'^[A-Za-z0-9_-]{1,80}$')


def artifacts_root():
    return Path(os.environ.get('ANALYTICS_ARTIFACTS_DIR', str(DEFAULT_ROOT))).resolve()


def read_json(path):
    try:
        if path.stat().st_size > 8 * 1024 * 1024:
            raise ValueError('Artifact exceeds size limit')
        return json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise HTTPException(503, 'Analytics snapshot is unavailable. Run the batch pipeline and try again.') from exc


def snapshot(requested_run=None):
    root = artifacts_root()
    if not (root / 'current.json').exists():
        raise HTTPException(503, {'status': 'not_ready', 'message': 'No completed analytics run. Run make analytics-demo first.'})
    identifier = requested_run or read_json(root / 'current.json').get('run_id', '')
    if not RUN_ID.fullmatch(identifier):
        raise HTTPException(422, 'Invalid run ID')
    directory = root / 'runs' / identifier
    if not directory.is_dir():
        raise HTTPException(404, 'Analytics run not found')
    manifest = read_json(directory / 'manifest.json')
    if manifest.get('status') != 'complete' or manifest.get('run_id') != identifier:
        raise HTTPException(503, 'Analytics run is incomplete')
    return directory, manifest


def metadata(manifest):
    return {k: manifest[k] for k in ['run_id', 'generated_at']}


def overview():
    directory, manifest = snapshot()
    result = read_json(directory / 'overview.json')
    status = artifacts_root() / 'status.json'
    result['pipeline'] = read_json(status) if status.exists() else {'status': 'complete'}
    end = date.fromisoformat(result['latest_session'])
    result['stale'] = (datetime.now(timezone.utc).date() - end).days > 7
    result['data_as_of'] = result['latest_session']
    acquisitions = {}
    for batch in manifest.get('input_manifests', []):
        for item in batch.get('downloads', []):
            acquisitions[(item['market'], item['ticker'])] = item
    result['acquisition'] = {
        'configured_stocks': len(acquisitions),
        'statuses': dict(Counter(item['status'] for item in acquisitions.values())),
        'failed_tickers': [item['ticker'] for item in acquisitions.values() if item['status'] in ('failed', 'empty')],
        'partial_tickers': [item['ticker'] for item in acquisitions.values() if item['status'] == 'partial'],
    }
    return result


def rankings(market, day, limit, run=None):
    directory, manifest = snapshot(run)
    summary = read_json(directory / 'overview.json')
    market_info = summary['markets'].get(market)
    if market_info is None:
        raise HTTPException(404, f'No saved analytics for market {market}')
    session = day.isoformat() if day else market_info['dates'][-1]
    if session not in market_info['dates']:
        raise HTTPException(404, 'No saved session for this date; select an available trading session')
    result = read_json(directory / 'rankings' / market / f'{session}.json')
    for key in ['gainers', 'losers', 'volatile', 'anomalies']:
        result[key] = result[key][:limit]
    return {**result, **metadata(manifest), 'data_as_of': session}


def stock(ticker, market, start, end, limit, run=None):
    if start and end and start > end:
        raise HTTPException(422, 'start must not be after end')
    directory, manifest = snapshot(run)
    summary = read_json(directory / 'overview.json')
    entry = next((s for s in summary['stocks'] if s['ticker'] == ticker and s['market'] == market), None)
    if entry is None:
        raise HTTPException(404, 'Stock is not available in this saved universe')
    # Only allow hashed stock artifact paths written by the publisher.
    if not re.fullmatch(r'stocks/[a-f0-9]{24}\.json', entry['file']):
        raise HTTPException(503, 'Invalid stock artifact manifest')
    result = read_json(directory / entry['file'])
    rows = [r for r in result['data'] if (not start or r['date'] >= start.isoformat())
            and (not end or r['date'] <= end.isoformat())]
    result.update(data=rows[-limit:], total_matching=len(rows), truncated=len(rows) > limit,
                  available_start=entry['start'], available_end=entry['end'], **metadata(manifest))
    return result


def benchmarks(run=None):
    _, manifest = snapshot(run)
    pointer_path = artifacts_root() / 'benchmark-current.json'
    empty = {'status': 'not_ready', **metadata(manifest), 'summaries': [],
             'message': 'Run make analytics-benchmark for this dataset.'}
    if not pointer_path.exists():
        return empty
    pointer = read_json(pointer_path)
    if pointer.get('run_id') != manifest['run_id']:
        return empty
    if not RUN_ID.fullmatch(pointer.get('directory', '')):
        raise HTTPException(503, 'Invalid benchmark artifact manifest')
    result = read_json(artifacts_root() / 'benchmarks' / pointer['directory'] / 'report.json')
    # Bounded history, keeping the newest measurement of each genuine dataset size.
    comparisons = {}
    for report in sorted((artifacts_root() / 'benchmarks').glob('*/report.json'))[-20:]:
        measurement = read_json(report)
        if measurement.get('run_id') == manifest['run_id']:
            comparisons[measurement['dataset_rows']] = {k: measurement[k] for k in
                ['dataset_rows', 'input_bytes', 'summaries', 'generated_at']}
    result['comparisons'] = [comparisons[size] for size in sorted(comparisons)]
    return result
