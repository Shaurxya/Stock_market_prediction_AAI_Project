"""
Batch Model Training Script
=============================
Trains LSTM and XGBoost models for all popular stocks in one go.

Usage:
    python train_all.py
    python train_all.py --market india
    python train_all.py --market us
    python train_all.py --market all
"""

import os
import sys
import time
import argparse

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from train_xgboost import train_xgboost
from train_lstm import train_lstm

# ─── Stock Lists ─────────────────────────────────────────────────────
US_STOCKS = [
    "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA",
    "NVDA", "META", "NFLX",
]

INDIA_NSE_STOCKS = [
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS",
    "ICICIBANK.NS", "SBIN.NS", "TATAMOTORS.NS", "WIPRO.NS",
    "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS", "LT.NS",
    "HCLTECH.NS", "AXISBANK.NS", "MARUTI.NS", "SUNPHARMA.NS",
]

SAVED_MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saved_models")


def is_already_trained(ticker: str) -> dict:
    """Check which models already exist for a ticker."""
    lstm_exists = os.path.exists(os.path.join(SAVED_MODELS_DIR, f"{ticker}_lstm_model.keras"))
    xgb_exists = os.path.exists(os.path.join(SAVED_MODELS_DIR, f"{ticker}_xgboost_model.pkl"))
    return {"lstm": lstm_exists, "xgboost": xgb_exists}


def train_stock(ticker: str, period: str = "5y", epochs: int = 50, skip_existing: bool = True):
    """Train both models for a single stock."""
    status = is_already_trained(ticker)

    print(f"\n{'='*60}")
    print(f"📊 Training models for: {ticker}")
    print(f"{'='*60}")

    # XGBoost
    if skip_existing and status["xgboost"]:
        print(f"   ⏭️  XGBoost already trained for {ticker}, skipping.")
    else:
        try:
            train_xgboost(ticker=ticker, period=period, tune=False)
            print(f"   ✅ XGBoost trained for {ticker}")
        except Exception as e:
            print(f"   ❌ XGBoost failed for {ticker}: {e}")

    # LSTM
    if skip_existing and status["lstm"]:
        print(f"   ⏭️  LSTM already trained for {ticker}, skipping.")
    else:
        try:
            train_lstm(ticker=ticker, period=period, epochs=epochs)
            print(f"   ✅ LSTM trained for {ticker}")
        except Exception as e:
            print(f"   ❌ LSTM failed for {ticker}: {e}")


def main():
    parser = argparse.ArgumentParser(description="Batch train models for all stocks")
    parser.add_argument("--market", type=str, default="all",
                        choices=["us", "india", "all"],
                        help="Which market to train: us, india, or all")
    parser.add_argument("--period", type=str, default="5y", help="Historical data period")
    parser.add_argument("--epochs", type=int, default=50, help="LSTM epochs")
    parser.add_argument("--force", action="store_true",
                        help="Re-train even if models already exist")
    args = parser.parse_args()

    stocks = []
    if args.market in ("us", "all"):
        stocks += US_STOCKS
    if args.market in ("india", "all"):
        stocks += INDIA_NSE_STOCKS

    print("=" * 60)
    print(f"🚀 Batch Training — {len(stocks)} stocks")
    print(f"   Market: {args.market.upper()}")
    print(f"   Period: {args.period} | LSTM Epochs: {args.epochs}")
    print(f"   Force retrain: {args.force}")
    print(f"   Stocks: {', '.join(stocks)}")
    print("=" * 60)

    start_time = time.time()
    success = 0
    failed = 0

    for i, ticker in enumerate(stocks, 1):
        print(f"\n[{i}/{len(stocks)}] {ticker}")
        try:
            train_stock(
                ticker=ticker,
                period=args.period,
                epochs=args.epochs,
                skip_existing=not args.force,
            )
            success += 1
        except Exception as e:
            print(f"   ❌ FAILED: {e}")
            failed += 1

    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"✅ Batch training complete!")
    print(f"   Successful: {success}/{len(stocks)}")
    print(f"   Failed: {failed}/{len(stocks)}")
    print(f"   Time: {elapsed/60:.1f} minutes")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
