"""
Dynamic Training Service (v2 — CORRECTED)
===========================================
Trains XGBoost (synchronous) and LSTM (background) models on-the-fly
for any stock ticker at request time.

FIXES APPLIED:
  1. Scaler fit ONLY on training data (no data leakage)
  2. LSTM uses the SAME scaler as XGBoost (scaler_params passed through)
  3. Sequence alignment fixed: features[i-59:i+1] → target[i]
  4. Lighter LSTM architecture (~12K params vs ~250K)
  5. Class weights for imbalanced up/down distribution
  6. ReduceLROnPlateau + EarlyStopping
  7. BatchNormalization for training stability
  8. Unidirectional LSTM (better for forecasting than bidirectional)
"""

import os
import sys
import json
import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Optional, Tuple, Any
from sklearn.preprocessing import MinMaxScaler

import xgboost as xgb

from app.services.feature_service import engineer_features, get_feature_columns
from app.services.model_cache import model_cache, ModelCacheEntry

logger = logging.getLogger(__name__)

# ─── Training Configuration ─────────────────────────────────────────
XGBOOST_CONFIG = {
    "n_estimators": 200,
    "max_depth": 5,
    "learning_rate": 0.05,
    "subsample": 0.9,
    "colsample_bytree": 0.9,
    "min_child_weight": 3,
    "gamma": 0.1,
    "reg_alpha": 0.1,
    "reg_lambda": 1.0,
    "objective": "binary:logistic",
    "eval_metric": "logloss",
    "random_state": 42,
    "use_label_encoder": False,
    "n_jobs": -1,
}

LSTM_CONFIG = {
    "lookback": 60,
    "epochs": 50,       # More epochs (early stopping controls actual count)
    "batch_size": 32,
    "learning_rate": 0.001,
    "patience": 8,      # Early stopping patience
    "lr_patience": 4,   # ReduceLR patience
}

TRAIN_SPLIT = 0.8
MIN_ROWS_REQUIRED = 100
TRAINING_TIMEOUT = 30  # seconds for XGBoost


def _prepare_sequences(data: np.ndarray, target: np.ndarray, lookback: int = 60):
    """
    CORRECTED sequence generation.

    Alignment: features[i-lookback+1 : i+1] → target[i]
    Uses features UP TO AND INCLUDING day i to predict day i → i+1.
    """
    X, y = [], []
    for i in range(lookback - 1, len(data) - 1):
        X.append(data[i - lookback + 1: i + 1])
        y.append(target[i])
    return np.array(X), np.array(y)


# ─── XGBoost Training (Synchronous) ─────────────────────────────────

def train_xgboost_for_ticker(ticker: str, df: pd.DataFrame) -> Tuple[Any, dict, dict]:
    """
    Train XGBoost for a specific ticker.
    FIX: Scaler fit ONLY on training data.
    """
    logger.info(f"   🏋️ Training XGBoost for {ticker}...")
    start_time = datetime.now()

    # ── Feature engineering ──────────────────────────────────────
    featured_df = engineer_features(df)
    feature_cols = get_feature_columns()

    if len(featured_df) < MIN_ROWS_REQUIRED:
        raise ValueError(
            f"Insufficient data for {ticker}: {len(featured_df)} rows after feature engineering "
            f"(need {MIN_ROWS_REQUIRED}+). Try a longer period."
        )

    # ── Create target variable ───────────────────────────────────
    featured_df = featured_df.copy()
    featured_df["Target"] = (featured_df["Close"].shift(-1) > featured_df["Close"]).astype(int)
    featured_df = featured_df.dropna()

    X = featured_df[feature_cols].values
    y = featured_df["Target"].values

    # ── FIX: Train/test split BEFORE scaling ─────────────────────
    split_idx = int(len(X) * TRAIN_SPLIT)
    X_train_raw, X_test_raw = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    # ── FIX: Scaler fit ONLY on training data ────────────────────
    scaler = MinMaxScaler(feature_range=(0, 1))
    X_train = scaler.fit_transform(X_train_raw)   # FIT on train
    X_test = scaler.transform(X_test_raw)          # TRANSFORM on test

    scaler_params = {
        "min_": scaler.min_.tolist(),
        "scale_": scaler.scale_.tolist(),
        "data_min_": scaler.data_min_.tolist(),
        "data_max_": scaler.data_max_.tolist(),
        "feature_columns": feature_cols,
        "fit_on": "training_data_only",
    }

    # ── Train XGBoost (uses UNSCALED data — XGBoost doesn't need scaling)
    model = xgb.XGBClassifier(**XGBOOST_CONFIG)
    model.fit(
        X_train_raw, y_train,
        eval_set=[(X_test_raw, y_test)],
        verbose=0,
    )

    # ── Evaluate ─────────────────────────────────────────────────
    from sklearn.metrics import accuracy_score, f1_score
    y_pred = model.predict(X_test_raw)
    accuracy = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred, zero_division=0)

    elapsed = (datetime.now() - start_time).total_seconds()

    metadata = {
        "ticker": ticker,
        "model_type": "XGBoost",
        "version": 2,
        "accuracy": round(accuracy, 4),
        "f1_score": round(f1, 4),
        "train_samples": int(X_train_raw.shape[0]),
        "test_samples": int(X_test_raw.shape[0]),
        "data_rows": len(featured_df),
        "feature_columns": feature_cols,
        "training_time_seconds": round(elapsed, 2),
        "trained_at": datetime.now().isoformat(),
        "config": XGBOOST_CONFIG,
    }

    logger.info(f"   ✅ XGBoost trained for {ticker} in {elapsed:.1f}s "
                f"(accuracy={accuracy:.3f}, f1={f1:.3f})")

    return model, scaler_params, metadata


# ─── LSTM Training (Background/Async) ───────────────────────────────

async def train_lstm_background(ticker: str, df: pd.DataFrame, scaler_params: dict):
    """
    Train LSTM model in background. Updates the cache when complete.
    FIX: Uses the SAME scaler_params as XGBoost for consistency.
    Gracefully skips if TensorFlow is not available (serverless mode).
    """
    try:
        import tensorflow as tf  # noqa: F401
    except ImportError:
        logger.info(f"   ⚠️ [Background] TensorFlow not available — skipping LSTM for {ticker}")
        return

    try:
        logger.info(f"   🔄 [Background] Starting LSTM training for {ticker}...")

        loop = asyncio.get_event_loop()
        lstm_model, lstm_meta = await loop.run_in_executor(
            None, _train_lstm_sync, ticker, df, scaler_params
        )

        if lstm_model is not None:
            model_cache.update_lstm(ticker, lstm_model)
            model_cache.save_to_disk(ticker, lstm_model=lstm_model)

            logger.info(f"   ✅ [Background] LSTM training complete for {ticker} "
                        f"(accuracy={lstm_meta.get('accuracy', 'N/A')})")
        else:
            logger.warning(f"   ⚠️ [Background] LSTM training returned None for {ticker}")

    except Exception as e:
        logger.error(f"   ❌ [Background] LSTM training failed for {ticker}: {e}")


def _train_lstm_sync(ticker: str, df: pd.DataFrame, scaler_params: dict) -> Tuple[Any, dict]:
    """
    CORRECTED synchronous LSTM training.

    Fixes:
    1. Uses SAME scaler as XGBoost (passed via scaler_params)
    2. Scaler fit on training data only
    3. Correct sequence alignment
    4. Lighter architecture (32→16 units)
    5. Class weights + ReduceLROnPlateau + BatchNorm
    """
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization
    from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau

    start_time = datetime.now()

    # Feature engineering
    featured_df = engineer_features(df)
    feature_cols = get_feature_columns()

    featured_df = featured_df.copy()
    featured_df["Target"] = (featured_df["Close"].shift(-1) > featured_df["Close"]).astype(int)
    featured_df = featured_df.dropna()

    X = featured_df[feature_cols].values
    y = featured_df["Target"].values

    # ── FIX: Split BEFORE scaling ────────────────────────────────
    split_idx = int(len(X) * TRAIN_SPLIT)
    X_train_raw = X[:split_idx]
    X_test_raw = X[split_idx:]
    y_train_all = y[:split_idx]
    y_test_all = y[split_idx:]

    # ── FIX: Recreate scaler from XGBoost's params (SAME scaler!) ─
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaler.min_ = np.array(scaler_params["min_"])
    scaler.scale_ = np.array(scaler_params["scale_"])
    scaler.data_min_ = np.array(scaler_params["data_min_"])
    scaler.data_max_ = np.array(scaler_params["data_max_"])
    scaler.n_features_in_ = len(scaler_params["min_"])
    scaler.n_samples_seen_ = 1

    X_train_scaled = scaler.transform(X_train_raw)
    X_test_scaled = scaler.transform(X_test_raw)

    # Clean NaN/Inf
    X_train_scaled = np.nan_to_num(X_train_scaled, nan=0.0, posinf=1.0, neginf=0.0)
    X_test_scaled = np.nan_to_num(X_test_scaled, nan=0.0, posinf=1.0, neginf=0.0)

    # ── FIX: Create sequences with corrected alignment ───────────
    lookback = LSTM_CONFIG["lookback"]
    X_train, y_train = _prepare_sequences(X_train_scaled, y_train_all, lookback)
    X_test, y_test = _prepare_sequences(X_test_scaled, y_test_all, lookback)

    if len(X_train) < 50:
        logger.warning(f"   ⚠️ Not enough sequences for LSTM: {len(X_train)}")
        return None, {}

    logger.info(f"   📦 LSTM sequences: train={X_train.shape}, test={X_test.shape}")
    logger.info(f"   📊 Target dist: train_up={y_train.mean():.2%}, test_up={y_test.mean():.2%}")

    # ── Class weights ────────────────────────────────────────────
    n_up = y_train.sum()
    n_down = len(y_train) - n_up
    class_weights = {
        0: len(y_train) / (2.0 * max(n_down, 1)),
        1: len(y_train) / (2.0 * max(n_up, 1)),
    }

    # ── FIX: Lighter architecture ────────────────────────────────
    model = Sequential([
        LSTM(32, return_sequences=True, input_shape=(lookback, len(feature_cols)),
             recurrent_dropout=0.1),
        BatchNormalization(),
        Dropout(0.15),

        LSTM(16, return_sequences=False, recurrent_dropout=0.1),
        BatchNormalization(),
        Dropout(0.15),

        Dense(8, activation="relu"),
        Dropout(0.1),

        Dense(1, activation="sigmoid"),
    ])
    model.compile(
        optimizer=tf.keras.optimizers.legacy.Adam(learning_rate=LSTM_CONFIG["learning_rate"]),
        loss="binary_crossentropy",
        metrics=["accuracy"],
    )

    # ── FIX: Added ReduceLROnPlateau ─────────────────────────────
    callbacks = [
        EarlyStopping(
            monitor="val_loss",
            patience=LSTM_CONFIG["patience"],
            restore_best_weights=True,
            verbose=0,
        ),
        ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.5,
            patience=LSTM_CONFIG["lr_patience"],
            min_lr=1e-6,
            verbose=0,
        ),
    ]

    model.fit(
        X_train, y_train,
        validation_data=(X_test, y_test),
        epochs=LSTM_CONFIG["epochs"],
        batch_size=LSTM_CONFIG["batch_size"],
        callbacks=callbacks,
        class_weight=class_weights,
        verbose=0,
    )

    # Evaluate
    from sklearn.metrics import accuracy_score, f1_score
    y_prob = model.predict(X_test, verbose=0).flatten()
    y_pred = (y_prob >= 0.5).astype(int)
    accuracy = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred, zero_division=0)

    elapsed = (datetime.now() - start_time).total_seconds()

    # Debug: check if model is actually learning
    if y_prob.std() < 0.05:
        logger.warning(f"   ⚠️ LSTM predictions nearly constant (std={y_prob.std():.4f})")

    meta = {
        "ticker": ticker,
        "model_type": "LSTM_v2",
        "accuracy": round(accuracy, 4),
        "f1_score": round(f1, 4),
        "prediction_std": round(float(y_prob.std()), 4),
        "training_time_seconds": round(elapsed, 2),
        "trained_at": datetime.now().isoformat(),
    }

    logger.info(f"   📊 LSTM trained for {ticker} in {elapsed:.1f}s "
                f"(accuracy={accuracy:.3f}, f1={f1:.3f}, pred_std={y_prob.std():.4f})")

    return model, meta


# ─── Orchestrator: Dynamic Training Pipeline ────────────────────────

async def get_or_train_model(ticker: str, df: pd.DataFrame) -> ModelCacheEntry:
    """
    Main orchestrator for the dynamic training pipeline.

    Flow:
    1. Check L1 memory cache → return if fresh
    2. Check L2 disk cache → return if fresh
    3. Acquire per-ticker lock (deduplicate concurrent requests)
    4. Train XGBoost synchronously
    5. Cache in L1 + L2
    6. Kick off LSTM training in background (with SAME scaler)
    7. Return cache entry for immediate prediction
    """
    ticker = ticker.upper()

    # ── Step 1 & 2: Check caches ─────────────────────────────────
    entry = model_cache.get_or_load_from_disk(ticker)
    if entry is not None and entry.has_xgboost():
        logger.info(f"   ✅ Using cached model for {ticker}")
        return entry

    # ── Step 3: Acquire per-ticker lock ──────────────────────────
    lock = await model_cache.get_ticker_lock(ticker)

    async with lock:
        # Double-check after acquiring lock
        entry = model_cache.get(ticker)
        if entry is not None and entry.has_xgboost():
            logger.info(f"   ✅ Model appeared in cache while waiting")
            return entry

        # ── Step 4: Train XGBoost synchronously ──────────────────
        async with model_cache.training_semaphore:
            model_cache.mark_training_start(ticker)
            try:
                logger.info(f"   🚀 Dynamic training pipeline started for {ticker}")

                loop = asyncio.get_event_loop()
                xgb_model, scaler_params, metadata = await loop.run_in_executor(
                    None, train_xgboost_for_ticker, ticker, df
                )

                # ── Step 5: Cache in L1 + L2 ─────────────────────
                model_cache.put(
                    ticker,
                    xgb_model=xgb_model,
                    scaler=scaler_params,
                    metadata=metadata,
                )
                model_cache.save_to_disk(
                    ticker,
                    xgb_model=xgb_model,
                    scaler_params=scaler_params,
                    metadata=metadata,
                )

                # ── Step 6: Background LSTM (with SAME scaler!) ──
                asyncio.create_task(
                    train_lstm_background(ticker, df, scaler_params)
                )

                logger.info(f"   ✅ Dynamic training complete for {ticker}")
                return model_cache.get(ticker)

            except Exception as e:
                logger.error(f"   ❌ Training failed for {ticker}: {e}")
                raise
            finally:
                model_cache.mark_training_done(ticker)
