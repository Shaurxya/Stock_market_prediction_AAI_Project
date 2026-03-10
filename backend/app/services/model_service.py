"""
Model Service (v2 — Dynamic Training)
=======================================
Handles model loading, prediction, and forecast generation.
Integrates with the ModelCache and TrainingService for dynamic training.

Changes from v1:
  - Uses ModelCache instead of raw file-based loading
  - Triggers dynamic training on cache miss via TrainingService
  - Supports both cached and freshly-trained models
  - LSTM is optional (may arrive later via background training)
"""

import os
import json
import numpy as np
import pandas as pd
import logging
from sklearn.preprocessing import MinMaxScaler

from app.services.feature_service import engineer_features, get_feature_columns
from app.services.model_cache import model_cache
from app.services.training_service import get_or_train_model

logger = logging.getLogger(__name__)

# ─── Configuration ───────────────────────────────────────────────────
LOOKBACK = 60  # Must match training


def _create_scaler(params: dict) -> MinMaxScaler:
    """Recreate MinMaxScaler from saved parameters."""
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaler.min_ = np.array(params["min_"])
    scaler.scale_ = np.array(params["scale_"])
    scaler.data_min_ = np.array(params["data_min_"])
    scaler.data_max_ = np.array(params["data_max_"])
    scaler.n_features_in_ = len(params["min_"])
    scaler.feature_range = (0, 1)
    scaler.n_samples_seen_ = 1
    return scaler


def _generate_30day_forecast(
    featured_df: pd.DataFrame,
    current_price: float,
    prediction: str,
    confidence: float,
    num_days: int = 30,
    num_simulations: int = 100,
) -> list:
    """
    Generate a 30-day price forecast using Monte Carlo simulation
    informed by technical indicators (RSI, MACD, trend, volatility).
    """
    from datetime import datetime, timedelta

    daily_returns = featured_df["Daily_Return"].dropna().values
    recent_returns = daily_returns[-60:]

    hist_volatility = float(featured_df["Volatility"].iloc[-1])
    if hist_volatility <= 0 or np.isnan(hist_volatility):
        hist_volatility = float(np.std(recent_returns)) if len(recent_returns) > 5 else 0.01

    mean_daily_return = float(np.mean(recent_returns))
    rsi = float(featured_df["RSI_14"].iloc[-1])
    macd_hist = float(featured_df["MACD_Histogram"].iloc[-1])
    sma_20 = float(featured_df["SMA_20"].iloc[-1])
    sma_50 = float(featured_df["SMA_50"].iloc[-1])

    direction = 1 if prediction == "Up" else -1
    drift = direction * abs(mean_daily_return) * (0.5 + confidence)

    if rsi > 75:
        drift -= 0.001
    elif rsi < 25:
        drift += 0.001

    macd_factor = np.clip(macd_hist / (current_price * 0.01 + 1e-9), -0.002, 0.002)
    drift += macd_factor * 0.3

    if sma_20 > sma_50:
        drift += 0.0003
    else:
        drift -= 0.0003

    all_paths = np.zeros((num_simulations, num_days))
    for s in range(num_simulations):
        price = current_price
        for d in range(num_days):
            decay = 1.0 - (d / (num_days * 3))
            day_drift = drift * max(decay, 0.3)
            shock = np.random.normal(0, hist_volatility)
            reversion = (sma_50 - price) / price * 0.01 if d > 10 else 0
            daily_change = day_drift + shock + reversion
            price = price * (1 + daily_change)
            price = max(price, current_price * 0.5)
            all_paths[s, d] = price

    median_path = np.median(all_paths, axis=0)
    high_band = np.percentile(all_paths, 80, axis=0)
    low_band = np.percentile(all_paths, 20, axis=0)

    today = datetime.now()
    forecast = []
    for d in range(num_days):
        forecast_date = today + timedelta(days=d + 1)
        while forecast_date.weekday() >= 5:
            forecast_date += timedelta(days=1)
        forecast.append({
            "day": d + 1,
            "date": forecast_date.strftime("%Y-%m-%d"),
            "price": round(float(median_path[d]), 2),
            "high": round(float(high_band[d]), 2),
            "low": round(float(low_band[d]), 2),
        })

    return forecast


async def get_predictions(ticker: str, df: pd.DataFrame) -> dict:
    """
    Generate predictions using dynamically trained models.
    
    Flow:
    1. Get or train model (via cache/training service)
    2. Engineer features on current data
    3. Run XGBoost prediction (always available)
    4. Run LSTM prediction (if model exists)
    5. Ensemble + 30-day forecast
    
    Now an async function to support the training pipeline.
    """
    result = {
        "lstm": None,
        "xgboost": None,
        "ensemble": None,
        "current_price": float(df["Close"].iloc[-1]),
        "forecast_prices": [],
        "model_info": {},  # NEW: training metadata
    }

    # ── Step 1: Get or train model dynamically ───────────────────
    try:
        cache_entry = await get_or_train_model(ticker, df)
    except Exception as e:
        logger.error(f"   ❌ Dynamic training failed for {ticker}: {e}")
        cache_entry = None

    # ── Step 2: Engineer features ────────────────────────────────
    featured_df = engineer_features(df)
    feature_cols = get_feature_columns()
    features = featured_df[feature_cols].values

    # Scale features using cached scaler or fit new
    if cache_entry and cache_entry.scaler:
        scaler = _create_scaler(cache_entry.scaler)
        features_scaled = scaler.transform(features)
    else:
        scaler = MinMaxScaler(feature_range=(0, 1))
        features_scaled = scaler.fit_transform(features)

    # Clean NaN/Inf from scaling (can occur if test data exceeds training range)
    features_scaled = np.nan_to_num(features_scaled, nan=0.0, posinf=1.0, neginf=0.0)

    # ── Step 3: XGBoost Prediction (uses UNSCALED features — trees are scale-invariant)
    if cache_entry and cache_entry.has_xgboost():
        try:
            X_input = features[-1:, :]  # Last row, unscaled
            xgb_prob = float(cache_entry.xgb_model.predict_proba(X_input)[:, 1][0])
            xgb_pred = "Up" if xgb_prob >= 0.5 else "Down"
            xgb_confidence = xgb_prob if xgb_pred == "Up" else (1 - xgb_prob)

            result["xgboost"] = {
                "prediction": xgb_pred,
                "confidence": round(xgb_confidence, 4),
                "probability_up": round(xgb_prob, 4),
                "probability_down": round(1 - xgb_prob, 4),
            }
            result["model_info"]["xgboost_accuracy"] = cache_entry.metadata.get("accuracy")
            result["model_info"]["trained_at"] = cache_entry.metadata.get("trained_at")
            result["model_info"]["training_time"] = cache_entry.metadata.get("training_time_seconds")
        except Exception as e:
            logger.warning(f"   ⚠️ XGBoost prediction error: {e}")

    # ── Step 4: LSTM Prediction (if available) ───────────────────
    if cache_entry and cache_entry.has_lstm() and len(features_scaled) >= LOOKBACK:
        try:
            X_input = features_scaled[-LOOKBACK:].reshape(1, LOOKBACK, len(feature_cols))
            lstm_prob = float(cache_entry.lstm_model.predict(X_input, verbose=0).flatten()[0])
            lstm_pred = "Up" if lstm_prob >= 0.5 else "Down"
            lstm_confidence = lstm_prob if lstm_pred == "Up" else (1 - lstm_prob)

            result["lstm"] = {
                "prediction": lstm_pred,
                "confidence": round(lstm_confidence, 4),
                "probability_up": round(lstm_prob, 4),
                "probability_down": round(1 - lstm_prob, 4),
            }
        except Exception as e:
            logger.warning(f"   ⚠️ LSTM prediction error: {e}")

    # ── Step 5: Ensemble ─────────────────────────────────────────
    probs = []
    if result["lstm"]:
        probs.append(result["lstm"]["probability_up"])
    if result["xgboost"]:
        probs.append(result["xgboost"]["probability_up"])

    if probs:
        avg_prob = np.mean(probs)
        ens_pred = "Up" if avg_prob >= 0.5 else "Down"
        ens_confidence = avg_prob if ens_pred == "Up" else (1 - avg_prob)

        result["ensemble"] = {
            "prediction": ens_pred,
            "confidence": round(float(ens_confidence), 4),
            "probability_up": round(float(avg_prob), 4),
            "probability_down": round(float(1 - avg_prob), 4),
        }

    # ── Fallback: Heuristic if no models ─────────────────────────
    if result["lstm"] is None and result["xgboost"] is None:
        logger.warning(f"   ⚠️ No models for {ticker}. Using heuristic.")
        recent_returns = featured_df["Daily_Return"].tail(10).mean()
        rsi = featured_df["RSI_14"].iloc[-1]
        macd_hist = featured_df["MACD_Histogram"].iloc[-1]

        score = 0
        score += 1 if recent_returns > 0 else -1
        score += 1 if 30 < rsi < 70 else (-1 if rsi > 70 else 0)
        score += 1 if macd_hist > 0 else -1

        heuristic_prob = max(0.2, min(0.8, 0.5 + (score * 0.1)))
        heuristic_pred = "Up" if heuristic_prob >= 0.5 else "Down"
        heuristic_conf = heuristic_prob if heuristic_pred == "Up" else (1 - heuristic_prob)

        fallback = {
            "prediction": heuristic_pred,
            "confidence": round(heuristic_conf, 4),
            "probability_up": round(heuristic_prob, 4),
            "probability_down": round(1 - heuristic_prob, 4),
        }
        result["lstm"] = fallback
        result["xgboost"] = fallback.copy()
        result["ensemble"] = fallback.copy()
        result["model_info"]["source"] = "heuristic_fallback"

    # ── Generate 30-Day Forecast ─────────────────────────────────
    ens = result.get("ensemble") or result.get("xgboost") or result.get("lstm")
    if ens:
        try:
            result["forecast_prices"] = _generate_30day_forecast(
                featured_df=featured_df,
                current_price=result["current_price"],
                prediction=ens["prediction"],
                confidence=ens["confidence"],
            )
            logger.info(f"   📈 30-day forecast generated for {ticker}")
        except Exception as e:
            logger.warning(f"   ⚠️ Forecast error: {e}")
            result["forecast_prices"] = []

    return result
