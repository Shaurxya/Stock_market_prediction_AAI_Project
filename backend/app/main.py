"""
FastAPI Backend — Stock Market Prediction System (v2)
======================================================
Main application entry point with dynamic training pipeline.
Configures CORS, routes, middleware, and logging.

Run with:
    uvicorn app.main:app --reload --port 8000
"""

import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from app.routes.predict import router as predict_router

# Load environment variables
load_dotenv()

# ─── Logging Configuration ───────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ─── Lifespan (startup/shutdown) ─────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager."""
    logger.info("🚀 Stock Market Prediction API starting...")
    logger.info("   📦 Dynamic training pipeline: ENABLED")
    logger.info("   💾 Model cache: INITIALIZED")
    logger.info("   🔧 Models will be trained on-demand per ticker")

    # Pre-load any existing models from disk (skip in serverless)
    try:
        from app.services.model_cache import model_cache, MODELS_DIR
        if os.path.exists(MODELS_DIR):
            import glob
            existing = glob.glob(os.path.join(MODELS_DIR, "*_xgboost_model.pkl"))
            if existing:
                tickers = [os.path.basename(f).replace("_xgboost_model.pkl", "") for f in existing]
                logger.info(f"   📂 Found {len(tickers)} pre-trained models: {tickers}")
            else:
                logger.info("   📂 No pre-trained models found. Will train dynamically.")
    except Exception as e:
        logger.info(f"   📂 Serverless mode — skipping disk cache: {e}")

    yield  # Application runs here

    logger.info("👋 Shutting down Stock Market Prediction API...")


# ─── App Configuration ───────────────────────────────────────────────
app = FastAPI(
    title="📈 Stock Market Prediction API",
    description=(
        "AI-powered stock market prediction system with dynamic model training. "
        "Uses LSTM and XGBoost models trained on-the-fly for any stock ticker. "
        "Supports US, Indian NSE, and BSE markets."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ─── CORS Configuration ──────────────────────────────────────────────
cors_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://localhost:3000,https://stock-market-prediction-aai-project.vercel.app"
)
origins = [origin.strip() for origin in cors_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Register Routes ─────────────────────────────────────────────────
app.include_router(predict_router, prefix="/api", tags=["Predictions"])


# ─── Root & Health Endpoints ─────────────────────────────────────────
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint — API welcome message."""
    return {
        "message": "📈 Stock Market Prediction API",
        "version": "2.0.0",
        "features": [
            "Dynamic per-stock model training",
            "XGBoost (sync) + LSTM (background)",
            "Model caching with TTL",
            "US + Indian market support",
        ],
        "docs": "/docs",
        "endpoints": {
            "predict": "POST /api/predict",
            "history": "GET /api/history/{ticker}",
            "health": "GET /api/health",
            "cache_stats": "GET /api/cache-stats",
        },
    }


@app.get("/api/health", tags=["Health"])
async def health_check():
    """Health check endpoint — verify API is running."""
    from app.services.model_cache import model_cache
    stats = model_cache.get_stats()
    return {
        "status": "healthy",
        "service": "Stock Market Prediction API",
        "version": "2.0.0",
        "dynamic_training": True,
        "cached_models": stats["cache_size"],
        "active_trainings": len(stats["training_in_progress"]),
    }
