"""
Utility Helpers
================
Helper functions for formatting API responses and data processing.
"""

from typing import Optional


def format_prediction_response(ticker: str, prediction_data: dict, stock_info: Optional[dict]) -> dict:
    """
    Format the raw prediction data into a clean API response.

    Args:
        ticker: Stock ticker symbol
        prediction_data: Raw prediction results from model_service
        stock_info: Stock metadata from yfinance

    Returns:
        Formatted response dictionary
    """
    predictions = []

    # LSTM prediction
    if prediction_data.get("lstm"):
        predictions.append({
            "model": "LSTM",
            "prediction": prediction_data["lstm"]["prediction"],
            "confidence": prediction_data["lstm"]["confidence"],
            "probability_up": prediction_data["lstm"]["probability_up"],
            "probability_down": prediction_data["lstm"]["probability_down"],
        })

    # XGBoost prediction
    if prediction_data.get("xgboost"):
        predictions.append({
            "model": "XGBoost",
            "prediction": prediction_data["xgboost"]["prediction"],
            "confidence": prediction_data["xgboost"]["confidence"],
            "probability_up": prediction_data["xgboost"]["probability_up"],
            "probability_down": prediction_data["xgboost"]["probability_down"],
        })

    # Ensemble
    ensemble = prediction_data.get("ensemble", {})
    ensemble_prediction = ensemble.get("prediction", "N/A")
    ensemble_confidence = ensemble.get("confidence", 0.0)

    # Market data
    market_data = None
    if stock_info:
        market_data = {
            "sector": stock_info.get("sector", "N/A"),
            "industry": stock_info.get("industry", "N/A"),
            "market_cap": stock_info.get("marketCap", None),
            "pe_ratio": stock_info.get("trailingPE", None),
            "52w_high": stock_info.get("fiftyTwoWeekHigh", None),
            "52w_low": stock_info.get("fiftyTwoWeekLow", None),
            "previous_close": stock_info.get("previousClose", None),
        }

    return {
        "ticker": ticker,
        "company_name": stock_info.get("shortName", ticker) if stock_info else ticker,
        "current_price": prediction_data.get("current_price"),
        "predictions": predictions,
        "ensemble_prediction": ensemble_prediction,
        "ensemble_confidence": ensemble_confidence,
        "forecast_prices": prediction_data.get("forecast_prices", []),
        "market_data": market_data,
        "model_info": prediction_data.get("model_info", {}),
    }


def format_number(value: float, decimals: int = 2) -> str:
    """Format a number with proper suffix (K, M, B, T)."""
    if value is None:
        return "N/A"

    if abs(value) >= 1e12:
        return f"${value / 1e12:.{decimals}f}T"
    elif abs(value) >= 1e9:
        return f"${value / 1e9:.{decimals}f}B"
    elif abs(value) >= 1e6:
        return f"${value / 1e6:.{decimals}f}M"
    elif abs(value) >= 1e3:
        return f"${value / 1e3:.{decimals}f}K"
    else:
        return f"${value:.{decimals}f}"
