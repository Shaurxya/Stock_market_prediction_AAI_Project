"""Offline API regression tests; run from the repo root with backend/venv/bin/python."""
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from app.main import app


class AnalyticsAPITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.env = patch.dict(os.environ, {'ANALYTICS_ARTIFACTS_DIR': str(self.root)})
        self.env.start()
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.env.stop()
        self.temp.cleanup()

    def publish(self):
        directory = self.root / 'runs' / 'test-run'
        filename = 'stocks/' + hashlib.sha256(b'fixture').hexdigest()[:24] + '.json'
        def write(path, data):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data))
        write(self.root / 'current.json', {'run_id': 'test-run'})
        write(directory / 'manifest.json', {'run_id': 'test-run', 'status': 'complete', 'generated_at': '2024-06-01T00:00:00+00:00'})
        write(directory / 'overview.json', {'status': 'ready', 'latest_session': '2024-05-31',
              'markets': {'US': {'dates': ['2024-05-30', '2024-05-31']}},
              'stocks': [{'ticker': 'AAA', 'market': 'US', 'file': filename, 'start': '2024-05-30', 'end': '2024-05-31'}]})
        write(directory / filename, {'ticker': 'AAA', 'data': [{'date': '2024-05-30'}, {'date': '2024-05-31'}]})
        write(directory / 'rankings/US/2024-05-31.json', {'date': '2024-05-31', 'breadth': {'stocks': 1},
              'gainers': [{'ticker': 'AAA'}], 'losers': [], 'volatile': [], 'anomalies': []})

    def test_not_ready_and_parameter_validation(self):
        response = self.client.get('/api/analytics/overview')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['detail']['status'], 'not_ready')
        for url in ['/api/analytics/rankings?market=XYZ', '/api/analytics/rankings?date=bad',
                    '/api/analytics/rankings?limit=100', '/api/analytics/stock/AAA?limit=10000',
                    '/api/analytics/rankings?run=../outside', '/api/analytics/stock/AAA?start=2024-06-02&end=2024-01-01']:
            self.assertEqual(self.client.get(url).status_code, 422, url)

    def test_saved_offline_routes_and_failed_refresh(self):
        self.publish()
        (self.root / 'status.json').write_text(json.dumps({'status': 'failed', 'error': 'injected'}))
        response = self.client.get('/api/analytics/overview')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['stale'])
        self.assertEqual(response.json()['pipeline']['status'], 'failed')
        self.assertEqual(self.client.get('/api/analytics/rankings').json()['date'], '2024-05-31')
        self.assertEqual(self.client.get('/api/analytics/rankings?date=2024-06-01').status_code, 404)
        self.assertEqual(self.client.get('/api/analytics/rankings?market=NSE').status_code, 404)
        response = self.client.get('/api/analytics/stock/aaa?limit=1')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['data']), 1)
        self.assertTrue(response.json()['truncated'])
        self.assertEqual(self.client.get('/api/analytics/stock/AAA?end=2020-01-01').json()['data'], [])
        self.assertEqual(self.client.get('/api/analytics/stock/NOPE').status_code, 404)
        self.assertEqual(self.client.get('/api/analytics/benchmarks').json()['status'], 'not_ready')

    def test_run_pinning_and_path_rejection(self):
        self.publish()
        self.assertEqual(self.client.get('/api/analytics/rankings?run=test-run').status_code, 200)
        self.assertEqual(self.client.get('/api/analytics/rankings?run=missing').status_code, 404)
        (self.root / 'current.json').write_text('{"run_id":"../outside"}')
        self.assertEqual(self.client.get('/api/analytics/overview').status_code, 422)

    def test_benchmark_comparisons_match_dataset_run(self):
        self.publish()
        def measurement(identifier, rows, run='test-run'):
            directory = self.root / 'benchmarks' / identifier
            directory.mkdir(parents=True)
            (directory / 'report.json').write_text(json.dumps({'status': 'ready', 'run_id': run,
                'dataset_rows': rows, 'input_bytes': 100, 'summaries': [], 'generated_at': '2024-06-01'}))
        measurement('measurement-1', 100)
        measurement('measurement-2', 200)
        measurement('measurement-3', 300, 'other-run')
        (self.root / 'benchmark-current.json').write_text(json.dumps({'run_id': 'test-run', 'directory': 'measurement-2'}))
        response = self.client.get('/api/analytics/benchmarks').json()
        self.assertEqual([r['dataset_rows'] for r in response['comparisons']], [100, 200])
        (self.root / 'benchmark-current.json').write_text(json.dumps({'run_id': 'old-run', 'directory': 'measurement-3'}))
        self.assertEqual(self.client.get('/api/analytics/benchmarks').json()['status'], 'not_ready')


class PredictionRegressionTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()

    def test_existing_endpoints(self):
        self.assertEqual(self.client.get('/api/health').json()['status'], 'healthy')
        self.assertGreater(len(self.client.get('/api/trending').json()['trending']), 10)
        self.assertEqual(self.client.get('/api/cache-stats').status_code, 200)

    def test_prediction_and_short_history_contract(self):
        import pandas as pd
        frame = pd.DataFrame({'Date': pd.bdate_range('2024-01-01', periods=150),
                              'Open': 100., 'High': 101., 'Low': 99., 'Close': 100., 'Volume': 1000})
        info = {'_resolved_ticker': 'TCS.NS', '_market': 'NSE', '_currency': 'INR', 'shortName': 'TCS'}
        prediction = {'current_price': 100, 'ensemble': {'prediction': 'Up', 'confidence': .6},
                      'xgboost': {'prediction': 'Up', 'confidence': .6, 'probability_up': .6, 'probability_down': .4}}
        with patch('app.routes.predict.fetch_live_stock_data', return_value=(frame, info)), patch(
                'app.routes.predict.get_predictions', new=AsyncMock(return_value=prediction)) as model:
            response = self.client.post('/api/predict', json={'ticker': 'TCS', 'market': 'NSE', 'force_retrain': True})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['currency'], 'INR')
            self.assertEqual(response.json()['ticker'], 'TCS.NS')
            self.assertEqual(response.json()['predictions'][0]['model'], 'XGBoost')
            model.assert_awaited_once_with('TCS.NS', frame, force_retrain=True)
        with patch('app.routes.predict.fetch_live_stock_data', return_value=(frame.head(20), info)):
            response = self.client.get('/api/history/TCS.NS?period=1mo')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.json()['data']), 20)


if __name__ == '__main__':
    unittest.main()
