"""
Feature Engineering Pipeline for Stock Market Prediction
=========================================================
Generates technical indicators and features from raw OHLCV data.
Features: SMA, EMA, RSI, MACD, Bollinger Bands, Lag features, etc.
"""

import numpy as np
import pandas as pd


def compute_sma(df: pd.DataFrame, column: str = "Close", windows: list = [20, 50]) -> pd.DataFrame:
    """Compute Simple Moving Averages."""
    for window in windows:
        df[f"SMA_{window}"] = df[column].rolling(window=window).mean()
    return df


def compute_ema(df: pd.DataFrame, column: str = "Close", spans: list = [12, 26]) -> pd.DataFrame:
    """Compute Exponential Moving Averages."""
    for span in spans:
        df[f"EMA_{span}"] = df[column].ewm(span=span, adjust=False).mean()
    return df


def compute_rsi(df: pd.DataFrame, column: str = "Close", period: int = 14) -> pd.DataFrame:
    """
    Compute Relative Strength Index (RSI).
    RSI measures the speed and magnitude of price movements.
    Values > 70 indicate overbought, < 30 indicate oversold.
    """
    delta = df[column].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()

    # Use Wilder's smoothing method after initial SMA
    for i in range(period, len(avg_gain)):
        avg_gain.iloc[i] = (avg_gain.iloc[i - 1] * (period - 1) + gain.iloc[i]) / period
        avg_loss.iloc[i] = (avg_loss.iloc[i - 1] * (period - 1) + loss.iloc[i]) / period

    rs = avg_gain / avg_loss
    df[f"RSI_{period}"] = 100 - (100 / (1 + rs))
    return df


def compute_macd(df: pd.DataFrame, column: str = "Close",
                 fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """
    Compute MACD (Moving Average Convergence Divergence).
    MACD = EMA_fast - EMA_slow
    Signal = EMA of MACD
    Histogram = MACD - Signal
    """
    ema_fast = df[column].ewm(span=fast, adjust=False).mean()
    ema_slow = df[column].ewm(span=slow, adjust=False).mean()

    df["MACD"] = ema_fast - ema_slow
    df["MACD_Signal"] = df["MACD"].ewm(span=signal, adjust=False).mean()
    df["MACD_Histogram"] = df["MACD"] - df["MACD_Signal"]
    return df


def compute_bollinger_bands(df: pd.DataFrame, column: str = "Close",
                            window: int = 20, num_std: float = 2.0) -> pd.DataFrame:
    """
    Compute Bollinger Bands.
    Upper Band = SMA + (num_std * rolling_std)
    Lower Band = SMA - (num_std * rolling_std)
    """
    sma = df[column].rolling(window=window).mean()
    rolling_std = df[column].rolling(window=window).std()

    df["BB_Upper"] = sma + (num_std * rolling_std)
    df["BB_Lower"] = sma - (num_std * rolling_std)
    df["BB_Width"] = df["BB_Upper"] - df["BB_Lower"]
    # Defensive: avoid division by zero
    bb_range = df["BB_Upper"] - df["BB_Lower"]
    df["BB_Position"] = np.where(bb_range != 0, (df[column] - df["BB_Lower"]) / bb_range, 0.5)
    return df


def compute_lag_features(df: pd.DataFrame, column: str = "Close", lags: int = 5) -> pd.DataFrame:
    """Create lag features for the specified column."""
    for lag in range(1, lags + 1):
        df[f"Lag_{lag}"] = df[column].shift(lag)
    return df


def compute_returns_and_volatility(df: pd.DataFrame, column: str = "Close",
                                    vol_window: int = 20) -> pd.DataFrame:
    """
    Compute daily returns, log returns, and rolling volatility.
    """
    df["Daily_Return"] = df[column].pct_change()
    # Defensive: avoid log(0) or log(negative)
    shifted = df[column].shift(1)
    safe_ratio = df[column] / shifted
    df["Log_Return"] = np.where(safe_ratio > 0, np.log(safe_ratio), 0.0)
    df["Volatility"] = df["Daily_Return"].rolling(window=vol_window).std()
    return df


def compute_volume_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute volume-based features."""
    df["Volume_SMA_20"] = df["Volume"].rolling(window=20).mean()
    # Defensive: avoid division by zero
    df["Volume_Ratio"] = np.where(
        df["Volume_SMA_20"] != 0,
        df["Volume"] / df["Volume_SMA_20"],
        1.0
    )
    return df


def compute_price_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute price-based features."""
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


def create_target(df: pd.DataFrame, column: str = "Close", horizon: int = 1) -> pd.DataFrame:
    """
    Create binary target variable.
    1 = Price goes UP in next `horizon` days
    0 = Price goes DOWN in next `horizon` days
    """
    df["Target"] = (df[column].shift(-horizon) > df[column]).astype(int)
    return df


def engineer_features(df: pd.DataFrame, include_target: bool = True) -> pd.DataFrame:
    """
    Main feature engineering pipeline.
    Applies all feature transformations to raw OHLCV data.

    Parameters:
        df: DataFrame with columns [Open, High, Low, Close, Volume]
        include_target: Whether to create the target variable

    Returns:
        DataFrame with all engineered features
    """
    print("🔧 Engineering features...")

    # Make a copy to avoid modifying the original
    data = df.copy()

    # Technical indicators
    data = compute_sma(data, windows=[20, 50])
    data = compute_ema(data, spans=[12, 26])
    data = compute_rsi(data, period=14)
    data = compute_macd(data)
    data = compute_bollinger_bands(data)

    # Lag features
    data = compute_lag_features(data, lags=5)

    # Returns and volatility
    data = compute_returns_and_volatility(data)

    # Volume features
    data = compute_volume_features(data)

    # Price features
    data = compute_price_features(data)

    # Target variable
    if include_target:
        data = create_target(data)

    # Drop rows with NaN values (from rolling calculations)
    initial_len = len(data)
    data = data.dropna()
    dropped = initial_len - len(data)
    print(f"   Dropped {dropped} rows with NaN values ({len(data)} remaining)")

    print(f"✅ Feature engineering complete. Shape: {data.shape}")
    print(f"   Features: {list(data.columns)}")

    return data


def get_feature_columns() -> list:
    """Return the list of feature column names used for model training."""
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


if __name__ == "__main__":
    # Quick test with sample data
    import yfinance as yf

    print("📥 Downloading sample data for AAPL...")
    ticker = yf.Ticker("AAPL")
    df = ticker.history(period="2y")
    df.reset_index(inplace=True)

    print(f"   Raw data shape: {df.shape}")
    print(f"   Date range: {df['Date'].min()} to {df['Date'].max()}")

    # Engineer features
    featured_df = engineer_features(df)
    print(f"\n📊 Final dataset preview:")
    print(featured_df.head())
    print(f"\n📈 Feature statistics:")
    print(featured_df[get_feature_columns()].describe())
