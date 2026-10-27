import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from analytics.common import COLUMNS, KEYS, spark_session
from analytics.features import METRICS, pandas_features, spark_features, pandas_aggregates, spark_aggregates
from analytics.ingest import import_csv, ingest
from analytics.pipeline import clean_data, process

FIXTURE = Path(__file__).parent / 'fixtures/daily.csv'


class CalculationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spark = spark_session()
        cls.raw = cls.spark.read.option('header', True).schema(', '.join(f'{c} STRING' for c in COLUMNS)).csv(str(FIXTURE))
        cls.clean, _, _ = clean_data(cls.raw)
        cls.clean = cls.clean.cache()
        cls.expected = pandas_features(cls.clean.drop('fetched_at').toPandas())
        cls.actual_spark = spark_features(cls.clean).cache()
        cls.actual = cls.actual_spark.drop('fetched_at').toPandas()

    @classmethod
    def tearDownClass(cls):
        cls.spark.stop()

    def test_pandas_spark_features_and_aggregates_agree(self):
        order = KEYS + ['date']
        left = self.expected.sort_values(order)
        right = self.actual.sort_values(order)
        for column in METRICS + ['gap_sessions', 'calendar_gap_days']:
            np.testing.assert_allclose(left[column], right[column], rtol=1e-8, atol=1e-10, equal_nan=True, err_msg=column)
        left_agg, left_rank = pandas_aggregates(self.expected)
        right_agg, right_rank = spark_aggregates(self.actual_spark)
        right_agg = right_agg.toPandas()
        for field in ['stocks', 'mean_return', 'advancing', 'declining', 'unchanged']:
            np.testing.assert_allclose(left_agg.sort_values(['market', 'date'])[field],
                                       right_agg.sort_values(['market', 'date'])[field], rtol=1e-9, atol=1e-10, equal_nan=True)
        right_rank = right_rank.drop('fetched_at').toPandas()
        self.assertEqual(left_rank.sort_values(['date', 'rank']).ticker.tolist(),
                         right_rank.sort_values(['date', 'rank']).ticker.tolist())

    def test_complete_windows_gap_and_split_adjustments(self):
        a = self.expected[self.expected.ticker == 'FIXTURE.A'].reset_index(drop=True)
        self.assertTrue(pd.isna(a.loc[18, 'sma_20']))
        self.assertAlmostEqual(a.loc[19, 'sma_20'], a.adj_close.head(20).mean())
        self.assertTrue(pd.isna(a.loc[19, 'volatility_20']))
        self.assertAlmostEqual(a.loc[20, 'volatility_20'], a.daily_return.iloc[1:21].std(ddof=1))
        self.assertAlmostEqual(a.loc[30, 'daily_return'], a.loc[30, 'adj_close'] / a.loc[29, 'adj_close'] - 1)
        self.assertLess(abs(a.loc[30, 'daily_return']), .1)  # raw split is roughly -50%
        self.assertTrue(pd.isna(a.loc[40, 'daily_return']))
        self.assertEqual(a.loc[40, 'gap_sessions'], 1)
        self.assertAlmostEqual(a.loc[20, 'volume_ratio'], a.loc[20, 'volume'] / a.volume.iloc[:20].mean())
        b = self.expected[self.expected.ticker == 'FIXTURE.B'].reset_index(drop=True)
        self.assertTrue(pd.isna(b.loc[20, 'volume_ratio']))
        c = self.expected[self.expected.ticker == 'FIXTURE.C'].reset_index(drop=True)
        self.assertTrue(c.loc[25:26, 'daily_return'].isna().all())

    def test_no_future_observations(self):
        prefix = self.clean.filter("date <= '2024-03-01'")
        result = spark_features(prefix).drop('fetched_at').toPandas().sort_values(KEYS + ['date'])
        expected = self.actual[pd.to_datetime(self.actual.date) <= pd.Timestamp('2024-03-01')].sort_values(KEYS + ['date'])
        np.testing.assert_allclose(result[METRICS], expected[METRICS], equal_nan=True, rtol=1e-9)

    def test_validation_and_deterministic_dedup(self):
        base = next(csv.DictReader(FIXTURE.open()))
        revised = {**base, 'close': '200', 'open': '200', 'high': '201', 'low': '199',
                   'fetched_at': '2024-06-02T00:00:00+00:00'}
        rows = [base, base, revised, {**base, 'ticker': '../bad'}, {**base, 'date': 'bad'},
                {**base, 'volume': '-1'}, {**base, 'open': 'NaN'}, {**base, 'high': '0'},
                {**base, 'close': 'not a number'}, {**base, 'currency': 'INR'},
                {**base, 'adj_close': '-1'}, {**base, 'fetched_at': 'bad'}]
        raw = self.spark.createDataFrame([[r[c] for c in COLUMNS] for r in rows], ', '.join(f'{c} STRING' for c in COLUMNS))
        clean, rejected, valid = clean_data(raw)
        self.assertEqual(clean.count(), 1)
        self.assertEqual(valid.count(), 3)
        self.assertEqual(rejected.count(), 9)
        self.assertEqual(clean.first()['close'], 200)


class IngestionTests(unittest.TestCase):
    def test_import_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            first = import_csv(FIXTURE, directory)
            second = import_csv(FIXTURE, directory)
            self.assertEqual(first['sha256'], second['sha256'])
            self.assertEqual(len(list(Path(directory).glob('raw/*/data.csv'))), 1)

    def test_unavailable_symbols_and_resume(self):
        stocks = [{'ticker': t, 'market': 'US', 'exchange': 'TEST', 'currency': 'USD'} for t in ['GOOD', 'BAD', 'EMPTY']]
        def download(stock, start, end, destination, retries):
            status = {'GOOD': 'success', 'BAD': 'failed', 'EMPTY': 'empty'}[stock['ticker']]
            result = {**stock, 'status': status, 'rows': 1 if status == 'success' else 0,
                      'requested_start': start, 'requested_end_exclusive': end, 'fetched_at': '2024-06-01T00:00:00Z'}
            if status == 'success':
                (destination / 'good.csv').write_text(FIXTURE.read_text())
                result.update(file='good.csv', actual_end='2024-05-01')
            return result
        with tempfile.TemporaryDirectory() as directory, patch('analytics.ingest._download', side_effect=download) as mock:
            first = ingest(stocks, directory, '2024-01-01', '2024-06-01')
            self.assertEqual({r['status'] for r in first['downloads']}, {'success', 'failed', 'empty'})
            mock.reset_mock()
            second = ingest(stocks, directory, '2024-01-01', '2024-06-01')
            self.assertEqual(mock.call_count, 2)
            self.assertIn('cached', {r['status'] for r in second['downloads']})

    def test_repeated_incremental_ingestion_retains_full_coverage(self):
        stock = {'ticker': 'GOOD', 'market': 'US', 'exchange': 'TEST', 'currency': 'USD'}
        starts = []
        def download(item, start, end, destination, retries):
            starts.append(start)
            (destination / 'data.csv').write_text(FIXTURE.read_text())
            return {**item, 'status': 'success', 'rows': 1, 'file': 'data.csv',
                    'requested_start': start, 'requested_end_exclusive': end,
                    'actual_end': str(pd.Timestamp(end).date() - pd.Timedelta(days=1)),
                    'fetched_at': end + 'T00:00:00Z'}
        with tempfile.TemporaryDirectory() as directory, patch('analytics.ingest._download', side_effect=download):
            ingest([stock], directory, '2020-01-01', '2024-06-01')
            ingest([stock], directory, '2020-01-01', '2024-06-02', incremental=True)
            ingest([stock], directory, '2020-01-01', '2024-06-03', incremental=True)
            self.assertEqual(starts, ['2020-01-01', '2024-05-21', '2024-05-22'])


class PublicationTests(unittest.TestCase):
    def test_repeat_counts_and_failed_publish_preserve_previous_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            data, artifacts = Path(temp) / 'data', Path(temp) / 'artifacts'
            import_csv(FIXTURE, data)
            first = process(data, artifacts)
            pointer = (artifacts / 'current.json').read_bytes()
            import_csv(FIXTURE, data)
            from analytics.pipeline import validate_snapshot
            def fail_after_validation(directory):
                validate_snapshot(directory)
                repeated = json.loads((directory / 'overview.json').read_text())
                self.assertEqual(first['records'], repeated['records'])
                raise ValueError('Injected pre-publication failure')
            with patch('analytics.pipeline.validate_snapshot', side_effect=fail_after_validation):
                with self.assertRaisesRegex(ValueError, 'Injected'):
                    process(data, artifacts)
            self.assertEqual(pointer, (artifacts / 'current.json').read_bytes())
            self.assertEqual(json.loads((artifacts / 'status.json').read_text())['status'], 'failed')


if __name__ == '__main__':
    unittest.main()
