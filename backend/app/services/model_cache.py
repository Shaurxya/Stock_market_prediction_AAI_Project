"""
Model Cache & Registry
=======================
3-layer caching system for dynamically trained models:
  L1: In-memory dict (TTL: 1 hour)
  L2: Disk persistence (TTL: 24 hours)
  L3: Retrain on cache miss

Includes:
  - Per-ticker asyncio locks to prevent duplicate training
  - Global semaphore to limit concurrent trainings
  - LRU eviction when memory cache exceeds max size
  - Model metadata tracking for versioning
"""

import os
import json
import time
import pickle
import asyncio
import logging
from typing import Optional, Tuple, Any
from collections import OrderedDict
from datetime import datetime

logger = logging.getLogger(__name__)

# ─── Configuration ───────────────────────────────────────────────────
# In serverless (Vercel), the project filesystem is read-only.
# Fall back to /tmp for model storage.
_default_models_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "models", "saved_models")
try:
    os.makedirs(_default_models_dir, exist_ok=True)
    MODELS_DIR = _default_models_dir
except OSError:
    MODELS_DIR = os.path.join("/tmp", "models", "saved_models")
    os.makedirs(MODELS_DIR, exist_ok=True)
    logger.info(f"Using /tmp for model storage (serverless mode)")

# Cache TTLs (seconds)
MEMORY_TTL = 3600        # 1 hour for in-memory cache
DISK_TTL = 86400         # 24 hours for disk cache
MARKET_HOURS_TTL = 14400 # 4 hours during market hours

# Limits
MAX_MEMORY_MODELS = 50         # Max tickers in memory
MAX_CONCURRENT_TRAININGS = 3   # Semaphore limit


class ModelCacheEntry:
    """Single cached model entry with metadata."""

    def __init__(self, ticker: str, xgb_model: Any = None, lstm_model: Any = None,
                 scaler: Any = None, metadata: dict = None):
        self.ticker = ticker
        self.xgb_model = xgb_model
        self.lstm_model = lstm_model
        self.scaler = scaler
        self.metadata = metadata or {}
        self.loaded_at = time.time()
        self.last_accessed = time.time()

    def touch(self):
        """Update last accessed timestamp."""
        self.last_accessed = time.time()

    @property
    def age_seconds(self) -> float:
        return time.time() - self.loaded_at

    @property
    def is_memory_expired(self) -> bool:
        return self.age_seconds > MEMORY_TTL

    def has_xgboost(self) -> bool:
        return self.xgb_model is not None

    def has_lstm(self) -> bool:
        return self.lstm_model is not None


class ModelCache:
    """
    Thread-safe model cache with per-ticker locking and LRU eviction.
    
    Usage:
        cache = ModelCache()
        entry = await cache.get("AAPL")
        if entry is None:
            async with cache.training_lock("AAPL"):
                # train model...
                cache.put("AAPL", xgb_model=model, metadata={...})
    """

    def __init__(self):
        self._cache: OrderedDict[str, ModelCacheEntry] = OrderedDict()
        self._ticker_locks: dict[str, asyncio.Lock] = {}
        self._locks_lock = asyncio.Lock()  # Lock for creating per-ticker locks
        self._training_semaphore = asyncio.Semaphore(MAX_CONCURRENT_TRAININGS)
        self._training_in_progress: set[str] = set()
        logger.info(f"ModelCache initialized (max_memory={MAX_MEMORY_MODELS}, "
                     f"max_concurrent={MAX_CONCURRENT_TRAININGS})")

    # ─── Public API ──────────────────────────────────────────────────

    def get(self, ticker: str) -> Optional[ModelCacheEntry]:
        """
        Get model from L1 memory cache.
        Returns None if not cached or expired.
        """
        ticker = ticker.upper()
        entry = self._cache.get(ticker)

        if entry is None:
            return None

        if entry.is_memory_expired:
            logger.info(f"   ⏰ Memory cache expired for {ticker} (age={entry.age_seconds:.0f}s)")
            del self._cache[ticker]
            return None

        # Move to end (LRU)
        self._cache.move_to_end(ticker)
        entry.touch()
        logger.info(f"   💾 Memory cache HIT for {ticker}")
        return entry

    def get_or_load_from_disk(self, ticker: str) -> Optional[ModelCacheEntry]:
        """
        Try L1 memory, then L2 disk. Returns None if both miss.
        """
        # L1: Memory
        entry = self.get(ticker)
        if entry is not None:
            return entry

        # L2: Disk
        return self._load_from_disk(ticker)

    def put(self, ticker: str, xgb_model: Any = None, lstm_model: Any = None,
            scaler: Any = None, metadata: dict = None):
        """
        Store model in L1 memory cache. Evicts LRU if at capacity.
        """
        ticker = ticker.upper()

        # Evict if at capacity
        while len(self._cache) >= MAX_MEMORY_MODELS:
            evicted_key, _ = self._cache.popitem(last=False)
            logger.info(f"   🗑️ Evicted {evicted_key} from memory cache (LRU)")

        entry = ModelCacheEntry(
            ticker=ticker,
            xgb_model=xgb_model,
            lstm_model=lstm_model,
            scaler=scaler,
            metadata=metadata or {},
        )
        self._cache[ticker] = entry
        logger.info(f"   💾 Cached {ticker} in memory ({len(self._cache)}/{MAX_MEMORY_MODELS})")

    def update_lstm(self, ticker: str, lstm_model: Any):
        """Update just the LSTM model for an existing cache entry."""
        ticker = ticker.upper()
        entry = self._cache.get(ticker)
        if entry:
            entry.lstm_model = lstm_model
            entry.loaded_at = time.time()
            logger.info(f"   ✅ Updated LSTM model in cache for {ticker}")

    async def get_ticker_lock(self, ticker: str) -> asyncio.Lock:
        """Get or create a per-ticker lock."""
        ticker = ticker.upper()
        async with self._locks_lock:
            if ticker not in self._ticker_locks:
                self._ticker_locks[ticker] = asyncio.Lock()
            return self._ticker_locks[ticker]

    def is_training(self, ticker: str) -> bool:
        """Check if a ticker is currently being trained."""
        return ticker.upper() in self._training_in_progress

    def mark_training_start(self, ticker: str):
        self._training_in_progress.add(ticker.upper())

    def mark_training_done(self, ticker: str):
        self._training_in_progress.discard(ticker.upper())

    @property
    def training_semaphore(self) -> asyncio.Semaphore:
        return self._training_semaphore

    def get_stats(self) -> dict:
        """Return cache statistics."""
        return {
            "cached_tickers": list(self._cache.keys()),
            "cache_size": len(self._cache),
            "max_size": MAX_MEMORY_MODELS,
            "training_in_progress": list(self._training_in_progress),
            "concurrent_limit": MAX_CONCURRENT_TRAININGS,
        }

    # ─── Disk Operations ─────────────────────────────────────────────

    def _load_from_disk(self, ticker: str) -> Optional[ModelCacheEntry]:
        """Load model from disk (L2 cache)."""
        ticker = ticker.upper()
        meta = self._load_metadata(ticker)

        if meta is None:
            logger.info(f"   📂 Disk cache MISS for {ticker}")
            return None

        # Check disk TTL
        trained_at = meta.get("trained_at", "")
        if trained_at:
            try:
                train_time = datetime.fromisoformat(trained_at)
                age = (datetime.now() - train_time).total_seconds()
                if age > DISK_TTL:
                    logger.info(f"   ⏰ Disk cache expired for {ticker} (age={age:.0f}s)")
                    return None
            except (ValueError, TypeError):
                pass

        # Load XGBoost
        xgb_model = self._load_pickle(ticker, "xgboost")

        # Load LSTM (optional, non-blocking)
        lstm_model = self._load_keras(ticker)

        # Load scaler
        scaler = self._load_scaler(ticker)

        if xgb_model is None and lstm_model is None:
            logger.info(f"   📂 No models found on disk for {ticker}")
            return None

        logger.info(f"   📂 Disk cache HIT for {ticker} "
                     f"(xgb={'✅' if xgb_model else '❌'}, lstm={'✅' if lstm_model else '❌'})")

        # Promote to L1
        self.put(ticker, xgb_model=xgb_model, lstm_model=lstm_model,
                 scaler=scaler, metadata=meta)
        return self._cache.get(ticker)

    def save_to_disk(self, ticker: str, xgb_model: Any = None,
                     lstm_model: Any = None, scaler_params: dict = None,
                     metadata: dict = None):
        """Persist model to disk (L2 cache). Gracefully handles read-only filesystems."""
        ticker = ticker.upper()

        try:
            if xgb_model is not None:
                path = os.path.join(MODELS_DIR, f"{ticker}_xgboost_model.pkl")
                with open(path, "wb") as f:
                    pickle.dump(xgb_model, f)
                logger.info(f"   💾 Saved XGBoost model to disk: {ticker}")

            if lstm_model is not None:
                try:
                    path = os.path.join(MODELS_DIR, f"{ticker}_lstm_model.keras")
                    lstm_model.save(path)
                    logger.info(f"   💾 Saved LSTM model to disk: {ticker}")
                except Exception as e:
                    logger.warning(f"   ⚠️ Could not save LSTM to disk: {e}")

            if scaler_params is not None:
                path = os.path.join(MODELS_DIR, f"{ticker}_scaler_params.json")
                with open(path, "w") as f:
                    json.dump(scaler_params, f, indent=2)

            if metadata is not None:
                meta_path = os.path.join(MODELS_DIR, f"{ticker}_model_meta.json")
                with open(meta_path, "w") as f:
                    json.dump(metadata, f, indent=2, default=str)
        except OSError as e:
            logger.warning(f"   ⚠️ Disk save failed (read-only filesystem?): {e}")

    def _load_metadata(self, ticker: str) -> Optional[dict]:
        meta_path = os.path.join(MODELS_DIR, f"{ticker}_model_meta.json")
        if not os.path.exists(meta_path):
            # Fallback: check for legacy results files
            for suffix in ["_xgboost_results.json", "_lstm_results.json"]:
                legacy = os.path.join(MODELS_DIR, f"{ticker}{suffix}")
                if os.path.exists(legacy):
                    with open(legacy, "r") as f:
                        return json.load(f)
            return None
        with open(meta_path, "r") as f:
            return json.load(f)

    def _load_pickle(self, ticker: str, model_type: str) -> Any:
        path = os.path.join(MODELS_DIR, f"{ticker}_{model_type}_model.pkl")
        if not os.path.exists(path):
            return None
        try:
            with open(path, "rb") as f:
                return pickle.load(f)
        except Exception as e:
            logger.warning(f"   ⚠️ Failed to load {model_type} for {ticker}: {e}")
            return None

    def _load_keras(self, ticker: str) -> Any:
        path = os.path.join(MODELS_DIR, f"{ticker}_lstm_model.keras")
        if not os.path.exists(path):
            return None
        try:
            import tensorflow as tf
            return tf.keras.models.load_model(path)
        except ImportError:
            logger.info(f"   ⚠️ TensorFlow not available — skipping LSTM load for {ticker}")
            return None
        except Exception as e:
            logger.warning(f"   ⚠️ Failed to load LSTM for {ticker}: {e}")
            return None

    def _load_scaler(self, ticker: str) -> Optional[dict]:
        path = os.path.join(MODELS_DIR, f"{ticker}_scaler_params.json")
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception:
            return None


# ─── Global Singleton ────────────────────────────────────────────────
model_cache = ModelCache()
