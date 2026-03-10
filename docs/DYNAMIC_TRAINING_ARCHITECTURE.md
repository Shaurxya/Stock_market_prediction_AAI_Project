# 🏗️ Dynamic Training Pipeline — Architecture Document

## 1. Architecture Overview

### Current State (Pre-trained)
```
User Request → Load Pre-trained Model → Predict → Response
               ⚠️ Only works for stocks with saved models (e.g., RELIANCE.NS)
               ⚠️ Falls back to heuristic for unknown tickers
```

### Target State (Dynamic Training)
```
User Request → Check Model Cache → [HIT] → Load & Predict → Response
                                 → [MISS] → Fetch Data → Train → Cache → Predict → Response
```

### System Design Diagram
```
┌──────────────┐     ┌───────────────────────────────────────────────────────┐
│  React       │     │  FastAPI Backend                                      │
│  Frontend    │────▶│                                                       │
│              │◀────│  ┌─────────┐   ┌──────────────┐   ┌───────────────┐  │
│  • Ticker    │     │  │ /predict│──▶│ Model Cache   │──▶│ Return        │  │
│    Input     │     │  │ Route   │   │ Registry      │   │ Prediction    │  │
│  • Results   │     │  └────┬────┘   │ (In-Memory +  │   └───────────────┘  │
│  • Charts    │     │       │        │  Disk TTL)    │                      │
│  • Forecast  │     │       ▼        └──────┬───────┘                      │
│              │     │  ┌─────────┐          │ MISS                         │
└──────────────┘     │  │ Training│◀─────────┘                              │
                     │  │ Pipeline│                                          │
                     │  │ (Async) │                                          │
                     │  └────┬────┘                                          │
                     │       │                                               │
                     │       ▼                                               │
                     │  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
                     │  │ Fetch    │─▶│ Feature  │─▶│ Train    │           │
                     │  │ yfinance │  │ Engineer │  │ XGBoost  │           │
                     │  └──────────┘  └──────────┘  │ (fast)   │           │
                     │                               └──────────┘           │
                     └───────────────────────────────────────────────────────┘
                                          │
                                          ▼
                     ┌───────────────────────────────────────────────────────┐
                     │  Disk-based Model Store                               │
                     │  models/saved_models/{TICKER}_xgboost_model.pkl      │
                     │  models/saved_models/{TICKER}_scaler_params.json     │
                     │  models/saved_models/{TICKER}_model_meta.json        │
                     └───────────────────────────────────────────────────────┘
```

---

## 2. Key Design Decisions

### 2.1 Synchronous vs Asynchronous Training

**Decision: Hybrid — Synchronous XGBoost + Optional Async LSTM**

| Factor | XGBoost (Sync) | LSTM (Async/Deferred) |
|--------|---------------|----------------------|
| Training time | 2-5 seconds | 30-120 seconds |
| Accuracy | Comparable | Slightly better for long sequences |
| User wait | Acceptable | Too long for real-time |
| Resource cost | Low (CPU only) | High (GPU preferred) |

**Strategy:**
- **XGBoost** trains synchronously at request time (~3s). Users get instant predictions.
- **LSTM** trains as a background task. Once complete, future requests use both models.
- If an LSTM model already exists on disk, load it. Otherwise, XGBoost-only is the immediate response.

### 2.2 Model Caching Strategy

```
┌─────────────────────────────────────────────────┐
│              3-Layer Cache                       │
├─────────────────────────────────────────────────┤
│ L1: In-Memory Dict     │ TTL: 1 hour            │
│     _model_cache[tick]  │ Fastest access          │
├─────────────────────────────────────────────────┤
│ L2: Disk (pickle/json)  │ TTL: 24 hours          │
│     saved_models/       │ Survives restarts       │
├─────────────────────────────────────────────────┤
│ L3: Retrain             │ When cache expired      │
│     Dynamic pipeline    │ Fresh model             │
└─────────────────────────────────────────────────┘
```

**Cache invalidation rules:**
- Model older than 24 hours → retrain
- Market hours (9:30 AM - 4 PM ET) → reduce TTL to 4 hours
- User can force retrain via `force_retrain=true` parameter

### 2.3 Avoiding Unnecessary Retraining

```python
# Pseudocode
def should_retrain(ticker):
    meta = load_model_metadata(ticker)
    if meta is None:
        return True  # Never trained
    if age(meta.trained_at) > MODEL_TTL:
        return True  # Stale
    if meta.data_rows < MIN_REQUIRED_ROWS:
        return True  # Insufficient data at last train
    return False  # Use cached model
```

### 2.4 Concurrent Request Handling

**Problem:** 10 users request TSLA simultaneously → 10 parallel trainings.

**Solution:** Per-ticker training locks using `asyncio.Lock`:
```
Request 1 (TSLA) → Acquires lock → Trains → Releases lock
Request 2 (TSLA) → Waits for lock → Lock released → Uses cached model
Request 3 (AAPL) → Different lock → Trains independently
```

### 2.5 Training Timeout Strategy

- XGBoost: Max 30 seconds (n_estimators capped at 200)
- LSTM: Max 120 seconds (epochs capped, early stopping patience=5)
- Global request timeout: 60 seconds for sync path
- If training fails → fall back to heuristic prediction (current behavior)

---

## 3. Request Flow (Step-by-Step)

```
1. POST /api/predict { ticker: "TSLA", period: "2y" }
2. Resolve ticker → "TSLA" (US market)
3. Check in-memory cache for "TSLA" model
   ├─ HIT + fresh → Skip to step 8
   └─ MISS or stale → Continue
4. Check disk cache for TSLA_xgboost_model.pkl + metadata
   ├─ EXISTS + fresh (< 24h) → Load into memory → Skip to step 8
   └─ MISSING or stale → Continue
5. Acquire training lock for "TSLA"
   ├─ Lock busy → Wait (another request is training) → Once done, use cached
   └─ Lock acquired → Continue
6. Fetch data via yfinance (2y history)
7. Train XGBoost dynamically
   a. Engineer features (same pipeline)
   b. Train/test split (80/20 chronological)
   c. Train XGBoost with fixed hyperparameters
   d. Evaluate (accuracy, F1)
   e. Save model + scaler + metadata to disk
   f. Load into memory cache
   g. [Background] Kick off LSTM training task
8. Generate prediction using cached model
9. Generate 30-day Monte Carlo forecast
10. Return response with prediction + confidence + metadata
```

---

## 4. Production Improvements

### 4.1 Fail-Safe Mechanisms
| Failure | Mitigation |
|---------|------------|
| yfinance API down | Retry 3x with backoff, then return error |
| Training crash | Catch exception, fall back to heuristic |
| Out of memory | Cap max concurrent trainings to 3 |
| Corrupt saved model | Delete and retrain on next request |
| Insufficient data (<100 rows) | Return 400 with clear message |

### 4.2 Model Versioning
```
models/saved_models/
├── AAPL_xgboost_model.pkl          # Current model
├── AAPL_model_meta.json            # Metadata (version, accuracy, timestamp)
├── AAPL_scaler_params.json         # Scaler for this version
└── AAPL_lstm_model.keras           # LSTM (if background-trained)
```

Metadata tracks: version, trained_at, data_rows, accuracy, f1, feature_columns.

### 4.3 Scaling for Multiple Users
- **Semaphore** limits concurrent trainings (default: 3)
- **Lock per ticker** prevents duplicate training
- **In-memory LRU cache** evicts least-used models (max 50 tickers)
- For true horizontal scaling: Redis for locks, S3 for model storage (future)

---

## 5. Tradeoffs: Dynamic vs Pre-trained

| Aspect | Pre-trained | Dynamic |
|--------|------------|---------|
| Coverage | Limited to trained tickers | Any ticker on yfinance |
| Freshness | Stale (trained once) | Retrained with latest data |
| Latency | ~100ms (just inference) | ~3-5s (first request) |
| Accuracy | Fixed | Adapts to each stock's patterns |
| Scalability | Excellent | Needs resource management |
| Complexity | Simple | More moving parts |

### When Dynamic Training is Appropriate
✅ Educational/demo systems (your use case)
✅ Low-to-medium traffic (< 100 concurrent users)
✅ When stock-specific models significantly outperform generic ones
✅ When model freshness matters

### When to Avoid
❌ High-frequency trading (latency critical)
❌ Thousands of concurrent users (use pre-trained + batch retrain)
❌ Regulatory environments requiring model audit trails

---

## 6. Performance Bottlenecks & Mitigations

| Bottleneck | Impact | Mitigation |
|-----------|--------|------------|
| yfinance rate limiting | Slow data fetch | Cache raw data for 1 hour |
| XGBoost training (200 trees) | ~3s per stock | Acceptable; reduce n_estimators if needed |
| LSTM training | 30-120s | Background only; never block response |
| Memory (many cached models) | ~5MB per model pair | LRU eviction at 50 models |
| Concurrent training | CPU saturation | Semaphore (max 3 concurrent) |
| Disk I/O for model save/load | ~200ms | Async disk I/O, memory-first |

---

## 7. Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `backend/app/services/training_service.py` | **NEW** | Dynamic training pipeline |
| `backend/app/services/model_cache.py` | **NEW** | 3-layer caching + locks |
| `backend/app/services/model_service.py` | **MODIFY** | Integrate with cache |
| `backend/app/routes/predict.py` | **MODIFY** | Add dynamic training flow |
| `backend/app/main.py` | **MODIFY** | Add startup/shutdown hooks |
| `backend/requirements.txt` | **MODIFY** | Add `filelock` dependency |
