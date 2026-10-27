"""Run with analytics/.venv/bin/python -m analytics.cli --help."""
import argparse
import json
from datetime import date, timedelta

from .common import ROOT


def main(argv=None):
    parser = argparse.ArgumentParser(description='StockAI historical analytics (local Spark, daily batches)')
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ['ingest', 'import-csv', 'process', 'demo', 'benchmark']:
        command = sub.add_parser(name)
        command.add_argument('--data-root', default=str(ROOT / 'datasets/market'))
        command.add_argument('--artifacts-root', default=str(ROOT / 'artifacts/analytics'))
        if name in ('ingest', 'demo'):
            command.add_argument('--universe', default=str(ROOT / 'analytics/config/universe.csv'))
            command.add_argument('--limit', type=int, default=20 if name == 'demo' else None)
            command.add_argument('--start', default=str(date.today() - timedelta(days=731)))
            command.add_argument('--end', default=str(date.today()), help='Exclusive session date')
            command.add_argument('--workers', type=int, choices=range(1, 5), default=2)
            command.add_argument('--retries', type=int, choices=range(1, 6), default=3)
            command.add_argument('--refresh', action='store_true', help='Full history refresh (corporate-action revisions)')
            command.add_argument('--incremental', action='store_true', help='Refetch last 10 calendar days plus new sessions')
        if name in ('process', 'demo', 'benchmark'):
            command.add_argument('--master', default='local[2]', choices=['local[1]', 'local[2]', 'local[4]'])
            command.add_argument('--partitions', type=int, default=4)
        if name in ('process', 'demo'):
            command.add_argument('--anomaly-threshold', type=float, default=2.0)
        if name == 'demo':
            command.add_argument('--offline', action='store_true', help='Use previously ingested files without provider calls')
        if name == 'import-csv':
            command.add_argument('path')
        if name in ('demo', 'benchmark'):
            command.add_argument('--repeats', type=int, choices=range(1, 11), default=3)
        if name == 'benchmark':
            command.add_argument('--max-rows', type=int, default=None, help='Benchmark a genuine stock/date-ordered subset')
    worker = sub.add_parser('_benchmark-worker', help=argparse.SUPPRESS)
    for key in ['engine', 'input', 'output', 'result', 'master']:
        worker.add_argument('--' + key, required=True)
    worker.add_argument('--partitions', type=int, required=True)
    args = parser.parse_args(argv)
    if hasattr(args, 'partitions') and not 1 <= args.partitions <= 64:
        parser.error('partitions must be between 1 and 64')
    if hasattr(args, 'anomaly_threshold') and not 0 < args.anomaly_threshold < 1000:
        parser.error('anomaly-threshold must be positive and below 1000')
    if hasattr(args, 'limit') and args.limit is not None and not 1 <= args.limit <= 1000:
        parser.error('limit must be between 1 and 1000')
    if getattr(args, 'max_rows', None) is not None and args.max_rows < 1:
        parser.error('max-rows must be positive')
    if args.command == '_benchmark-worker':
        from .benchmark import worker
        worker(args.engine, args.input, args.output, args.result, args.master, args.partitions)
        return
    if args.command == 'import-csv':
        from .ingest import import_csv
        result = import_csv(args.path, args.data_root)
    if args.command in ('ingest', 'demo') and not getattr(args, 'offline', False):
        from .ingest import ingest, load_universe
        result = ingest(load_universe(args.universe, args.limit), args.data_root, args.start, args.end,
                        args.workers, args.retries, args.refresh, args.incremental)
        print(json.dumps(result, indent=2))
        if args.command == 'ingest':
            return
    if args.command in ('process', 'demo'):
        from .pipeline import process
        result = process(args.data_root, args.artifacts_root, args.master, args.partitions, args.anomaly_threshold)
        print(json.dumps({k: result[k] for k in ['run_id', 'records', 'stocks_count', 'quality', 'execution']}, indent=2))
        if args.command == 'process':
            return
    if args.command in ('benchmark', 'demo'):
        from .benchmark import benchmark
        result = benchmark(args.artifacts_root, args.repeats, args.master, args.partitions, max_rows=getattr(args, 'max_rows', None))
    print(json.dumps(result, indent=2, default=str))


if __name__ == '__main__':
    main()
