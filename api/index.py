"""
Vercel Serverless Entry Point
==============================
Exposes the FastAPI app as a Vercel serverless function.
All /api/* routes are handled by FastAPI.
"""

import os
import sys
import logging

logger = logging.getLogger(__name__)

# Vercel runs from the project root. Add backend/ to sys.path
# so that 'from app.main import app' resolves correctly.
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_backend_dir = os.path.join(_project_root, "backend")

for _p in [_backend_dir, _project_root]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Import the FastAPI app
try:
    from app.main import app  # noqa: E402
except Exception as e:
    # If the main app fails to import, create a minimal fallback
    # so we can diagnose the issue from the browser
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    app = FastAPI(title="StockAI API (Fallback)")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    _import_error = str(e)

    @app.get("/api/health")
    async def health():
        return {"status": "fallback", "error": _import_error}

    @app.get("/api/trending")
    async def trending():
        return {
            "error": _import_error,
            "trending": [
                {"ticker": "AAPL", "name": "Apple Inc.", "sector": "Technology", "market": "US"},
                {"ticker": "GOOGL", "name": "Alphabet Inc.", "sector": "Technology", "market": "US"},
                {"ticker": "MSFT", "name": "Microsoft Corp.", "sector": "Technology", "market": "US"},
                {"ticker": "RELIANCE.NS", "name": "Reliance Industries", "sector": "Energy", "market": "NSE"},
                {"ticker": "TCS.NS", "name": "Tata Consultancy", "sector": "Technology", "market": "NSE"},
                {"ticker": "INFY.NS", "name": "Infosys Ltd.", "sector": "Technology", "market": "NSE"},
            ],
        }

    @app.get("/api/{path:path}")
    async def catch_all(path: str):
        return {"error": _import_error, "path": path}

    logger.error(f"Failed to import main app: {e}")
