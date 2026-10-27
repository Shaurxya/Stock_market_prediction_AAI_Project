import sys
import unittest
from pathlib import Path
from unittest.mock import patch, AsyncMock

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.feature_service import engineer_features
from app.services.model_service import _generate_30day_forecast
from app.services.training_service import _labeled_features, _prepare_sequences, train_xgboost_for_ticker, _schedule_lstm
from app.services.data_service import _fetch_with_retries
from app.services.model_cache import ModelCache, ModelCacheEntry


def fixture():
    generator = np.random.default_rng(42)
    prices = 100 * np.exp(np.cumsum(generator.normal(0, .01, 500)))
    return pd.DataFrame({'Date': pd.bdate_range(end='2024-06-07', periods=500),
                         'Open': prices, 'High': prices + 1, 'Low': prices - 1,
                         'Close': prices, 'Volume': generator.integers(1000, 3000, 500)})


class ModelCorrectnessTests(unittest.TestCase):
    def test_disk_cache_does_not_mix_old_lstm_with_new_scaler(self):
        cache = ModelCache()
        with patch.object(cache, '_load_metadata', return_value={'lstm_ready': False}), patch.object(
                cache, '_load_pickle', return_value=object()), patch.object(cache, '_load_keras') as keras, patch.object(
                cache, '_load_scaler', return_value={'scale_': [1]}):
            entry = cache.get_or_load_from_disk('FIXTURE')
            self.assertTrue(entry.has_xgboost())
            self.assertFalse(entry.has_lstm())
            keras.assert_not_called()

    def test_one_month_history_does_not_require_fifty_rows(self):
        data = fixture().tail(20)
        with patch('app.services.data_service.yf.Ticker') as stock:
            stock.return_value.history.return_value = data
            stock.return_value.info = {'shortName': 'Fixture'}
            result, info = _fetch_with_retries('FIXTURE', '1mo')
            self.assertEqual(len(result), 20)
            stock.return_value.history.assert_called_once_with(period='1mo', auto_adjust=True)

    def test_unknown_last_target_excluded_and_sequences_aligned(self):
        data = fixture()
        features = _labeled_features(data)
        self.assertEqual(features.Date.iloc[-1], data.Date.iloc[-2])
        expected = (data.Close.shift(-1) > data.Close).iloc[:-1]
        np.testing.assert_array_equal(features.Target, expected.loc[features.index].astype(int))
        X, y = _prepare_sequences(np.arange(10).reshape(10, 1), np.arange(10), lookback=3)
        self.assertEqual(len(X), 8)
        np.testing.assert_array_equal(X[-1].flatten(), [7, 8, 9])
        self.assertEqual(y[-1], 9)

    def test_forecast_dates_unique_weekdays_after_last_observation(self):
        data = engineer_features(fixture())
        result = _generate_30day_forecast(data, float(data.Close.iloc[-1]), 'Up', .6)
        dates = pd.to_datetime([r['date'] for r in result])
        self.assertEqual(len(set(dates)), 30)
        self.assertTrue(all(d.weekday() < 5 for d in dates))
        self.assertTrue(all(d > data.Date.iloc[-1] for d in dates))
        self.assertEqual(dates[0], pd.Timestamp('2024-06-10'))

    def test_rsi_flat_series_remains_usable(self):
        data = fixture()
        for column in ['Open', 'Close', 'High', 'Low']:
            data[column] = 100.
        featured = engineer_features(data)
        self.assertFalse(featured.empty)
        self.assertTrue((featured.RSI_14 == 50).all())

    def test_xgboost_chronological_training_and_scaler(self):
        data = fixture()
        model, scaler, meta = train_xgboost_for_ticker('FIXTURE', data)
        labeled = _labeled_features(data)
        boundary = int(len(labeled) * .8)
        columns = scaler['feature_columns']
        np.testing.assert_allclose(scaler['data_max_'], labeled[columns].iloc[:boundary - 1].max())
        self.assertEqual(meta['train_samples'], boundary - 1)
        self.assertEqual(meta['test_samples'], len(labeled) - boundary)
        self.assertAlmostEqual(model.predict_proba(labeled[columns].values[-1:]).sum(), 1, places=6)


class BackgroundTrainingTests(unittest.IsolatedAsyncioTestCase):
    async def test_pending_background_training_scheduled_once(self):
        import asyncio
        entry = ModelCacheEntry('FIXTURE', scaler={'scale_': [1]}, metadata={'lstm_status': 'pending'})
        with patch('app.services.training_service.train_lstm_background', new=AsyncMock()) as train:
            _schedule_lstm('FIXTURE', None, entry)
            _schedule_lstm('FIXTURE', None, entry)
            await asyncio.sleep(0)
            train.assert_awaited_once()


if __name__ == '__main__':
    unittest.main()
