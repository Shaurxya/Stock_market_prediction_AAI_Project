"""
Prediction API Routes (v2 — Dynamic Training)
===============================================
Handles stock prediction requests with on-the-fly model training.
Supports US, Indian NSE (.NS), and Indian BSE (.BO) markets.
Production-safe with comprehensive error handling and defensive checks.

Changes from v1:
  - get_predictions is now async (supports dynamic training)
  - Added force_retrain parameter
  - Added /cache-stats endpoint for monitoring
  - Added model_info to response
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
import traceback
import logging

from app.services.data_service import (
    fetch_live_stock_data, get_stock_info,
    resolve_ticker, detect_market, POPULAR_INDIAN_STOCKS,
)
from app.services.model_service import get_predictions
from app.services.model_cache import model_cache
from app.utils.helpers import format_prediction_response

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── Request/Response Models ─────────────────────────────────────────

class PredictRequest(BaseModel):
    """Request body for stock prediction."""
    ticker: str = Field(
        ...,
        description="Stock ticker symbol (e.g., AAPL, RELIANCE.NS, TCS)",
        examples=["AAPL"]
    )
    period: str = Field(
        default="2y",
        description="Historical data period (e.g., 1y, 2y, 5y)",
        examples=["2y"]
    )
    market: str = Field(
        default="auto",
        description="Market: 'US', 'NSE', 'BSE', or 'auto' for auto-detection",
        examples=["auto"]
    )
    force_retrain: bool = Field(
        default=False,
        description="Force model retraining even if cached model exists",
    )


class PredictionResult(BaseModel):
    """Individual model prediction result."""
    model: str
    prediction: str  # "Up" or "Down"
    confidence: float
    probability_up: float
    probability_down: float


class PredictResponse(BaseModel):
    """Full prediction response."""
    model_config = {"protected_namespaces": ()}

    ticker: str
    company_name: Optional[str] = None
    current_price: Optional[float] = None
    predictions: List[PredictionResult]
    ensemble_prediction: str
    ensemble_confidence: float
    forecast_prices: Optional[List[dict]] = None
    market_data: Optional[dict] = None
    market: Optional[str] = None
    currency: Optional[str] = None
    model_info: Optional[dict] = None  # Training metadata


class HistoryResponse(BaseModel):
    """Historical data response."""
    ticker: str
    period: str
    data: List[dict]
    stats: dict


# ─── Routes ──────────────────────────────────────────────────────────

@router.post("/predict", response_model=PredictResponse)
async def predict_stock(request: PredictRequest):
    """
    🔮 Predict stock price direction using dynamically trained models.

    If no trained model exists for the requested ticker, the system will:
    1. Fetch historical data from yfinance
    2. Train an XGBoost model on-the-fly (~3-5 seconds)
    3. Cache the model for future requests
    4. Begin LSTM training in the background

    - **ticker**: Stock symbol (e.g., AAPL, RELIANCE, TCS.NS)
    - **period**: Historical data period for analysis
    - **market**: 'US', 'NSE', 'BSE', or 'auto'
    - **force_retrain**: Set to true to force retraining
    """
    ticker = request.ticker.upper().strip()
    period = request.period
    market = request.market.upper().strip() if request.market else "auto"

    # Normalize market value
    if market not in ("US", "NSE", "BSE", "AUTO"):
        market = "auto"
    else:
        market = market.lower() if market == "AUTO" else market

    try:
        # ── Validate ticker ──────────────────────────────────────
        if not ticker or len(ticker) > 20:
            raise HTTPException(
                status_code=400,
                detail="Invalid ticker symbol. Must be 1-20 characters."
            )

        # ── Resolve ticker based on market ───────────────────────
        resolved = resolve_ticker(ticker, market)

        # ── Force retrain: clear cache if requested ──────────────
        if request.force_retrain:
            logger.info(f"   🔄 Force retrain requested for {resolved}")
            # This will cause a cache miss and trigger retraining
            cache = model_cache.get(resolved)
            if cache:
                model_cache._cache.pop(resolved.upper(), None)

        # ── Fetch live stock data ────────────────────────────────
        logger.info(f"📥 Prediction request: {ticker} → {resolved} "
                     f"(market={market}, period={period})")

        df, stock_info = fetch_live_stock_data(ticker, period, market)

        # ── Defensive: No data → try extended period ─────────────
        if df is None or df.empty:
            logger.info(f"   🔄 Retrying {ticker} with extended period '5y'...")
            df, stock_info = fetch_live_stock_data(ticker, "5y", market)

            if df is None or df.empty:
                raise HTTPException(
                    status_code=404,
                    detail=f"No data found for ticker '{ticker}'. "
                           f"Tried: {resolved}. "
                           f"Please verify the symbol is correct."
                )

        # ── Defensive: Minimum data requirement ──────────────────
        if len(df) < 100:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient data for {resolved}. "
                       f"Need at least 100 trading days, got {len(df)}. "
                       f"Try a longer period like '5y'."
            )

        logger.info(f"   📊 Data ready: {len(df)} rows for {resolved}")

        # ── Get predictions (now async — may trigger training) ───
        logger.info(f"   🔮 Generating predictions for {resolved}...")
        prediction_data = await get_predictions(resolved, df)

        if prediction_data is None:
            raise HTTPException(
                status_code=500,
                detail=f"Model prediction returned no results for '{resolved}'."
            )

        # ── Format response ──────────────────────────────────────
        response = format_prediction_response(ticker, prediction_data, stock_info)

        resolved_market = stock_info.get("_market", detect_market(resolved)) if stock_info else detect_market(resolved)
        response["market"] = resolved_market
        response["currency"] = stock_info.get("_currency", "INR" if resolved_market in ("NSE", "BSE") else "USD") if stock_info else "USD"
        response["ticker"] = resolved
        response["model_info"] = prediction_data.get("model_info", {})

        logger.info(f"   ✅ Prediction complete for {resolved} ({resolved_market})")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"   ❌ Error predicting {ticker}: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed for '{ticker}': {str(e)}"
        )


@router.get("/history/{ticker}", response_model=HistoryResponse)
async def get_history(ticker: str, period: str = "1y", market: str = "auto"):
    """
    📊 Get historical stock price data for charting.
    Supports US, NSE, and BSE markets.

    - **ticker**: Stock symbol (e.g., AAPL, RELIANCE.NS)
    - **period**: Data period (1mo, 3mo, 6mo, 1y, 2y, 5y)
    - **market**: 'US', 'NSE', 'BSE', or 'auto'
    """
    ticker = ticker.upper().strip()

    try:
        df, stock_info = fetch_live_stock_data(ticker, period, market)

        if df is None or df.empty:
            raise HTTPException(
                status_code=404,
                detail=f"No historical data found for '{ticker}'."
            )

        # Convert to list of dicts for JSON response
        history_data = []
        for _, row in df.iterrows():
            history_data.append({
                "date": row["Date"].strftime("%Y-%m-%d") if hasattr(row["Date"], "strftime") else str(row["Date"]),
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
                "close": round(float(row["Close"]), 2),
                "volume": int(row["Volume"]),
            })

        # Calculate stats
        resolved_market = stock_info.get("_market", "US") if stock_info else "US"
        currency = stock_info.get("_currency", "USD") if stock_info else "USD"

        stats = {
            "current_price": round(float(df["Close"].iloc[-1]), 2),
            "high_52w": round(float(df["Close"].tail(252).max()), 2),
            "low_52w": round(float(df["Close"].tail(252).min()), 2),
            "avg_volume": int(df["Volume"].mean()),
            "total_records": len(df),
            "date_range": f"{history_data[0]['date']} to {history_data[-1]['date']}",
            "market": resolved_market,
            "currency": currency,
        }

        if stock_info:
            stats["company_name"] = stock_info.get("shortName", ticker)
            stats["market_cap"] = stock_info.get("marketCap", None)
            stats["sector"] = stock_info.get("sector", None)

        return HistoryResponse(
            ticker=stock_info.get("_resolved_ticker", ticker) if stock_info else ticker,
            period=period,
            data=history_data,
            stats=stats,
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error fetching history for {ticker}: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch history for '{ticker}': {str(e)}"
        )


@router.get("/trending")
async def get_trending():
    """
    📈 Get popular stock tickers for US and Indian markets.
    """
    trending = {
        "trending": [
            # US Stocks
            {"ticker": "AAPL", "name": "Apple Inc.", "sector": "Technology", "market": "US"},
            {"ticker": "GOOGL", "name": "Alphabet Inc.", "sector": "Technology", "market": "US"},
            {"ticker": "MSFT", "name": "Microsoft Corp.", "sector": "Technology", "market": "US"},
            {"ticker": "AMZN", "name": "Amazon.com Inc.", "sector": "Consumer Cyclical", "market": "US"},
            {"ticker": "TSLA", "name": "Tesla Inc.", "sector": "Automotive", "market": "US"},
            {"ticker": "NVDA", "name": "NVIDIA Corp.", "sector": "Technology", "market": "US"},
            {"ticker": "META", "name": "Meta Platforms", "sector": "Technology", "market": "US"},
            {"ticker": "NFLX", "name": "Netflix Inc.", "sector": "Communication", "market": "US"},
            # Indian NSE Stocks
            {"ticker": "RELIANCE.NS", "name": "Reliance Industries", "sector": "Energy", "market": "NSE"},
            {"ticker": "TCS.NS", "name": "Tata Consultancy", "sector": "Technology", "market": "NSE"},
            {"ticker": "INFY.NS", "name": "Infosys Ltd.", "sector": "Technology", "market": "NSE"},
            {"ticker": "HDFCBANK.NS", "name": "HDFC Bank", "sector": "Financial", "market": "NSE"},
            {"ticker": "ICICIBANK.NS", "name": "ICICI Bank", "sector": "Financial", "market": "NSE"},
            {"ticker": "SBIN.NS", "name": "State Bank of India", "sector": "Financial", "market": "NSE"},
            {"ticker": "TATAMOTORS.NS", "name": "Tata Motors", "sector": "Automotive", "market": "NSE"},
            {"ticker": "WIPRO.NS", "name": "Wipro Ltd.", "sector": "Technology", "market": "NSE"},
        ],
    }
    return trending


@router.get("/cache-stats")
async def cache_stats():
    """
    📊 Get model cache statistics for monitoring.
    Shows cached tickers, active trainings, and memory usage.
    """
    return model_cache.get_stats()
