"""
Feature Engineering Service
============================
Applies technical indicator features to stock data for model inference.
Same pipeline as used during training — ensures consistency.
Production-safe with defensive checks after dropna().
"""

import numpy as np
import pandas as pd


def compute_sma(df: pd.DataFrame, column: str = "Close", windows: list = [20, 50]) -> pd.DataFrame:
    for window in windows:
        df[f"SMA_{window}"] = df[column].rolling(window=window).mean()
    return df


def compute_ema(df: pd.DataFrame, column: str = "Close", spans: list = [12, 26]) -> pd.DataFrame:
    for span in spans:
        df[f"EMA_{span}"] = df[column].ewm(span=span, adjust=False).mean()
    return df


def compute_rsi(df: pd.DataFrame, column: str = "Close", period: int = 14) -> pd.DataFrame:
    delta = df[column].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()

    for i in range(period, len(avg_gain)):
        avg_gain.iloc[i] = (avg_gain.iloc[i - 1] * (period - 1) + gain.iloc[i]) / period
        avg_loss.iloc[i] = (avg_loss.iloc[i - 1] * (period - 1) + loss.iloc[i]) / period

    rs = avg_gain / avg_loss
    df[f"RSI_{period}"] = 100 - (100 / (1 + rs))
    return df


def compute_macd(df: pd.DataFrame, column: str = "Close") -> pd.DataFrame:
    ema_fast = df[column].ewm(span=12, adjust=False).mean()
    ema_slow = df[column].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema_fast - ema_slow
    df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_Histogram"] = df["MACD"] - df["MACD_Signal"]
    return df


def compute_bollinger_bands(df: pd.DataFrame, column: str = "Close", window: int = 20) -> pd.DataFrame:
    sma = df[column].rolling(window=window).mean()
    rolling_std = df[column].rolling(window=window).std()
    df["BB_Upper"] = sma + (2.0 * rolling_std)
    df["BB_Lower"] = sma - (2.0 * rolling_std)
    df["BB_Width"] = df["BB_Upper"] - df["BB_Lower"]
    # Defensive: avoid division by zero
    bb_range = df["BB_Upper"] - df["BB_Lower"]
    df["BB_Position"] = np.where(bb_range != 0, (df[column] - df["BB_Lower"]) / bb_range, 0.5)
    return df


def compute_lag_features(df: pd.DataFrame, column: str = "Close", lags: int = 5) -> pd.DataFrame:
    for lag in range(1, lags + 1):
        df[f"Lag_{lag}"] = df[column].shift(lag)
    return df


def compute_returns_and_volatility(df: pd.DataFrame, column: str = "Close") -> pd.DataFrame:
    df["Daily_Return"] = df[column].pct_change()
    # Defensive: avoid log(0) or log(negative)
    shifted = df[column].shift(1)
    safe_ratio = df[column] / shifted
    df["Log_Return"] = np.where(safe_ratio > 0, np.log(safe_ratio), 0.0)
    df["Volatility"] = df["Daily_Return"].rolling(window=20).std()
    return df


def compute_volume_features(df: pd.DataFrame) -> pd.DataFrame:
    df["Volume_SMA_20"] = df["Volume"].rolling(window=20).mean()
    # Defensive: avoid division by zero
    df["Volume_Ratio"] = np.where(
        df["Volume_SMA_20"] != 0,
        df["Volume"] / df["Volume_SMA_20"],
        1.0
    )
    return df


def compute_price_features(df: pd.DataFrame) -> pd.DataFrame:
    # Defensive: avoid division by zero
    df["High_Low_Range"] = np.where(
        df["Close"] != 0,
        (df["High"] - df["Low"]) / df["Close"],
        0.0
    )
    df["Open_Close_Range"] = np.where(
        df["Open"] != 0,
        (df["Close"] - df["Open"]) / df["Open"],
        0.0
    )
    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply all feature engineering steps to raw OHLCV data.
    This must match the training pipeline exactly.

    Returns engineered DataFrame. May return empty DataFrame if
    insufficient data survives the dropna() step.
    """
    if df is None or df.empty:
        print("   ⚠️ Feature engineering received empty DataFrame")
        return pd.DataFrame()

    data = df.copy()
    initial_len = len(data)

    data = compute_sma(data, windows=[20, 50])
    data = compute_ema(data, spans=[12, 26])
    data = compute_rsi(data, period=14)
    data = compute_macd(data)
    data = compute_bollinger_bands(data)
    data = compute_lag_features(data, lags=5)
    data = compute_returns_and_volatility(data)
    data = compute_volume_features(data)
    data = compute_price_features(data)

    data = data.dropna()

    dropped = initial_len - len(data)
    print(f"   🔧 Feature engineering: {initial_len} → {len(data)} rows ({dropped} dropped)")

    if data.empty:
        print("   ⚠️ All rows dropped during feature engineering! Need more historical data.")

    return data


def get_feature_columns() -> list:
    """Feature columns used by the models — must match training."""
    return [
        "Open", "High", "Low", "Close", "Volume",
        "SMA_20", "SMA_50",
        "EMA_12", "EMA_26",
        "RSI_14",
        "MACD", "MACD_Signal", "MACD_Histogram",
        "BB_Upper", "BB_Lower", "BB_Width", "BB_Position",
        "Lag_1", "Lag_2", "Lag_3", "Lag_4", "Lag_5",
        "Daily_Return", "Log_Return", "Volatility",
        "Volume_SMA_20", "Volume_Ratio",
        "High_Low_Range", "Open_Close_Range",
    ]
