"""
Data Service
=============
Handles fetching stock data from Yahoo Finance.
Supports US, Indian NSE (.NS), and Indian BSE (.BO) tickers.
Production-safe with retry logic, market detection, and defensive checks.
"""

import time
import yfinance as yf
import pandas as pd
from typing import Tuple, Optional


# ─── Constants ───────────────────────────────────────────────────────
VALID_PERIODS = ["1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "max"]
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds

# ─── Indian Stock Detection ─────────────────────────────────────────
# Common Indian stock symbols (base names without suffix)
POPULAR_INDIAN_STOCKS = {
    "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "HINDUNILVR",
    "SBIN", "BHARTIARTL", "ITC", "KOTAKBANK", "LT", "HCLTECH",
    "AXISBANK", "ASIANPAINT", "MARUTI", "SUNPHARMA", "TITAN",
    "ULTRACEMCO", "BAJFINANCE", "BAJAJFINSV", "WIPRO", "ONGC",
    "NTPC", "POWERGRID", "TATAMOTORS", "TATASTEEL", "JSWSTEEL",
    "TECHM", "ADANIENT", "ADANIPORTS", "COALINDIA", "GRASIM",
    "DRREDDY", "CIPLA", "EICHERMOT", "DIVISLAB", "BPCL",
    "HEROMOTOCO", "INDUSINDBK", "BRITANNIA", "NESTLEIND",
    "APOLLOHOSP", "TATACONSUM", "HINDALCO", "M&M", "HDFCLIFE",
    "SBILIFE", "UPL", "SHREECEM",
}


def detect_market(ticker: str) -> str:
    """
    Detect market from ticker string.

    Returns:
        'NSE' | 'BSE' | 'US'
    """
    upper = ticker.upper().strip()

    if upper.endswith(".NS"):
        return "NSE"
    if upper.endswith(".BO"):
        return "BSE"

    # Check if the base symbol is a known Indian stock
    base = upper.split(".")[0]
    if base in POPULAR_INDIAN_STOCKS:
        return "NSE"  # Default Indian stocks to NSE

    return "US"


def resolve_ticker(ticker: str, market: str = "auto") -> str:
    """
    Resolve a user-entered ticker to a yfinance-compatible format.

    Args:
        ticker: Raw user input (e.g., "RELIANCE", "TCS.NS", "AAPL")
        market: Market hint — "US", "NSE", "BSE", or "auto"

    Returns:
        Resolved ticker string (e.g., "RELIANCE.NS", "AAPL")
    """
    ticker = ticker.upper().strip().replace(" ", "")

    # Already has a suffix → respect it
    if ticker.endswith(".NS") or ticker.endswith(".BO"):
        return ticker

    # Market explicitly specified
    if market == "NSE":
        return f"{ticker}.NS"
    elif market == "BSE":
        return f"{ticker}.BO"
    elif market == "US":
        return ticker

    # Auto-detect
    detected = detect_market(ticker)
    if detected == "NSE":
        return f"{ticker}.NS"
    elif detected == "BSE":
        return f"{ticker}.BO"

    return ticker


def _sanitize_period(period: str) -> str:
    """Ensure period is valid for yfinance."""
    if period not in VALID_PERIODS:
        print(f"   ⚠️ Invalid period '{period}', defaulting to '2y'")
        return "2y"
    return period


def fetch_live_stock_data(
    ticker: str,
    period: str = "2y",
    market: str = "auto"
) -> Tuple[Optional[pd.DataFrame], Optional[dict]]:
    """
    Fetch live stock data from Yahoo Finance with retry logic.
    Supports US, NSE, and BSE markets.

    Args:
        ticker: Stock ticker symbol (e.g., "AAPL", "RELIANCE", "TCS.NS")
        period: Data period (e.g., "1y", "2y", "5y")
        market: Market hint — "US", "NSE", "BSE", or "auto"

    Returns:
        Tuple of (DataFrame with OHLCV data, stock info dict)
    """
    resolved = resolve_ticker(ticker, market)
    period = _sanitize_period(period)
    detected_market = detect_market(resolved)

    print(f"   🌐 Market: {detected_market} | Resolved ticker: {resolved}")

    # ── Build a list of ticker variants to try ───────────────────
    # If auto-detected, also try without suffix (in case it's actually US)
    ticker_variants = [resolved]

    if market == "auto" and not (ticker.endswith(".NS") or ticker.endswith(".BO")):
        base = ticker.upper().strip()
        # If we auto-added .NS, also try raw (maybe it's US)
        if resolved.endswith(".NS"):
            ticker_variants.append(base)
        # If raw, also try .NS (maybe it's Indian)
        elif not resolved.endswith(".BO"):
            ticker_variants.append(f"{base}.NS")

    # ── Try each variant with retries ────────────────────────────
    for variant in ticker_variants:
        df, info = _fetch_with_retries(variant, period)
        if df is not None and not df.empty:
            # Inject the resolved market info into the info dict
            if info is None:
                info = {"shortName": variant}
            info["_resolved_ticker"] = variant
            info["_market"] = "NSE" if variant.endswith(".NS") else ("BSE" if variant.endswith(".BO") else "US")
            info["_currency"] = "INR" if variant.endswith((".NS", ".BO")) else "USD"
            return df, info

    print(f"   ❌ No data found for any variant of '{ticker}': {ticker_variants}")
    return None, None


def _fetch_with_retries(
    ticker: str, period: str
) -> Tuple[Optional[pd.DataFrame], Optional[dict]]:
    """Fetch stock data with retry logic for a single ticker variant."""

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"   📥 Attempt {attempt}/{MAX_RETRIES} — {ticker} (period={period})...")
            stock = yf.Ticker(ticker)

            df = stock.history(period=period)

            # ── Defensive Check 1: Empty DataFrame ───────────────
            if df is None or df.empty:
                print(f"   ⚠️ Attempt {attempt}: Empty data for {ticker}")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY)
                    continue
                return None, None

            # ── Defensive Check 2: Reset index safely ────────────
            if "Date" not in df.columns:
                df.reset_index(inplace=True)

            # ── Defensive Check 3: Ensure required columns exist ─
            required_cols = ["Open", "High", "Low", "Close", "Volume"]
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                print(f"   ❌ Missing columns: {missing_cols}")
                return None, None

            # ── Defensive Check 4: Drop NaN rows in OHLCV ───────
            initial_len = len(df)
            df = df.dropna(subset=required_cols)
            if len(df) < initial_len:
                print(f"   🧹 Cleaned {initial_len - len(df)} NaN rows ({len(df)} remaining)")

            # ── Defensive Check 5: Minimum data threshold ────────
            if len(df) < 50:
                print(f"   ⚠️ Only {len(df)} rows for {ticker}. Minimum 50 needed.")
                return None, None

            # ── Get stock info (non-critical) ────────────────────
            info = _safe_get_info(stock, ticker)

            print(f"   ✅ Fetched {len(df)} rows for {ticker}")
            return df, info

        except Exception as e:
            print(f"   ⚠️ Attempt {attempt} error for {ticker}: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)

    return None, None


def _safe_get_info(stock, ticker: str) -> dict:
    """Safely get stock info — never let this crash the pipeline."""
    try:
        info = stock.info
        if info and isinstance(info, dict) and len(info) > 2:
            return info
    except Exception as e:
        print(f"   ⚠️ Could not fetch info for {ticker}: {e}")
    return {"shortName": ticker}


def get_stock_info(ticker: str, market: str = "auto") -> Optional[dict]:
    """
    Get detailed stock information.

    Returns:
        Dictionary with stock metadata (name, sector, market cap, etc.)
    """
    resolved = resolve_ticker(ticker, market)

    try:
        stock = yf.Ticker(resolved)
        info = stock.info

        return {
            "shortName": info.get("shortName", resolved),
            "longName": info.get("longName", resolved),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "marketCap": info.get("marketCap", None),
            "previousClose": info.get("previousClose", None),
            "open": info.get("open", None),
            "dayHigh": info.get("dayHigh", None),
            "dayLow": info.get("dayLow", None),
            "volume": info.get("volume", None),
            "fiftyTwoWeekHigh": info.get("fiftyTwoWeekHigh", None),
            "fiftyTwoWeekLow": info.get("fiftyTwoWeekLow", None),
            "trailingPE": info.get("trailingPE", None),
            "dividendYield": info.get("dividendYield", None),
            "currency": info.get("currency", "USD"),
        }
    except Exception as e:
        print(f"   ⚠️ Could not fetch info for {resolved}: {e}")
        return {"shortName": resolved}
