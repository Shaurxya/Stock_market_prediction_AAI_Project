# 🔍 LSTM Debug Analysis — Stock Market Prediction System

## Critical Bugs Found

### 🐛 Bug 1: SCALER MISMATCH (Severity: CRITICAL)
**File:** `training_service.py` → `_train_lstm_sync()` + `model_service.py`

The LSTM and XGBoost train **separate scalers independently**, but at inference time
the XGBoost's scaler is loaded and used for BOTH models.

```python
# XGBoost training: fits scaler A, saves scaler_params A to disk
scaler = MinMaxScaler()
X_scaled = scaler.fit_transform(X)   # → Scaler A

# LSTM training (_train_lstm_sync): fits scaler B (DIFFERENT!)
scaler = MinMaxScaler()
X_scaled = scaler.fit_transform(X)   # → Scaler B (different fit!)

# Inference (model_service.py): loads Scaler A for BOTH models
scaler = _create_scaler(cache_entry.scaler)     # ← Scaler A
X_input = features_scaled[-LOOKBACK:]            # ← Scaled with A
lstm_prob = cache_entry.lstm_model.predict(X_input)  # ← LSTM expects Scaler B!
```

**Result:** LSTM receives differently-scaled input than what it was trained on → garbage predictions.

---

### 🐛 Bug 2: DATA LEAKAGE IN SCALER (Severity: HIGH)
**File:** `train_lstm.py` (line 239), `training_service.py` (line 105, 210)

The scaler is fit on the ENTIRE dataset before train/test split:
```python
features_scaled = scaler.fit_transform(features)   # Fits on ALL data
# ... THEN splits into train/test
X_train, X_test = X[:split_idx], X[split_idx:]     # Test data already in scaler!
```

**Result:** Test set statistics leak into the scaler → inflated accuracy metrics, the
model "knows" future value ranges.

**Fix:** Fit scaler ONLY on training data, then `transform()` the test data.

---

### 🐛 Bug 3: SEQUENCE-TARGET MISALIGNMENT (Severity: HIGH)
**File:** `training_service.py` → `_train_lstm_sync()`, `train_lstm.py` (line 81-94)

Training vs inference inconsistency:
```python
# TRAINING: sequence = features[i-60 : i], target = target[i]
# The sequence ends at day i-1, predicts day i → i+1

# INFERENCE (model_service.py):
X_input = features_scaled[-LOOKBACK:]   # Includes TODAY's features
# Predicts... what? Model never saw "current day features" → predict next day
```

The model was trained using features up to day `i-1` to predict day `i→i+1`.
At inference, it gets features up to TODAY and predicts... ambiguously.

**Fix:** Consistent alignment — use features up to and including day i to predict i→i+1.

---

### 🐛 Bug 4: OVER-PARAMETERIZED ARCHITECTURE (Severity: MEDIUM)
**File:** `train_lstm.py` (line 107-121)

```
BiLSTM(128) → 256 units (bidirectional doubles)
LSTM(64)    → 64 units
Dense(32)   → 32 units
Dense(1)    → 1 unit
Total params: ~250,000+
```

With only ~300-400 training sequences (2y data, 60-day lookback), this model has
~250K parameters learning from ~300 samples. That's 800+ parameters per sample.

**Rule of thumb:** You want at least 10-50x more samples than parameters.
Here you have 0.001x — the model will either overfit or fail to converge.

**Fix:** Much lighter architecture (32→16 units, ~5K params).

---

### 🐛 Bug 5: EXCESSIVE DROPOUT STACKING (Severity: MEDIUM)
**File:** `train_lstm.py` (line 112-118)

```python
Dropout(0.3)   # After BiLSTM — drops 30%
Dropout(0.3)   # After LSTM  — drops 30% of remaining
Dropout(0.2)   # After Dense — drops 20% of remaining
# Cumulative: only 0.7 × 0.7 × 0.8 = 39% of activations survive!
```

With a small dataset and small model, this much dropout starves the network of signal.
The model can't learn because too much information is discarded at every layer.

---

## Additional Issues

### Issue 6: Bidirectional LSTM for Time-Series
Bidirectional processes the sequence forward AND backward. The backward pass "sees"
the end of the sequence first. For forecasting, this can learn patterns that
exploit future context — patterns that won't exist at inference time.

### Issue 7: Raw Prices as Features
Features include raw Close, Open, High, Low, Lag_1-5, SMA, EMA, BB bands — all
in absolute price space. For a PER-STOCK model, MinMaxScaler handles this, but
these features are highly correlated (>0.99 correlation between Close, Lag_1,
SMA_20, EMA_12, etc.), which can confuse gradient-based optimization.

### Issue 8: No Class Weighting
Stock markets have ~53% up days. Without class weights, the model may develop
a bias toward always predicting "Up" to maximize accuracy.

### Issue 9: No Learning Rate Scheduling
The fixed lr=0.001 with Adam may be too high once the model approaches a
local minimum, causing oscillation and preventing convergence.

---

## Debug Checklist

Run these checks if LSTM predictions are constant or poor:

- [ ] Print `y_prob` distribution — if all values cluster near 0.5, model isn't learning
- [ ] Print `y_train` class balance — if >60% one class, add class weights
- [ ] Check training loss — if it doesn't decrease, lr is too high or architecture is wrong
- [ ] Check val_loss — if it increases while train_loss decreases, overfitting
- [ ] Verify scaler is fit ONLY on training data
- [ ] Verify same scaler is used for training and inference
- [ ] Print `X_train.shape` — expect (samples, 60, n_features)
- [ ] Print `features_scaled` range — should be [0, 1] for training data
- [ ] Check for NaN/Inf in features after scaling
- [ ] Verify y values are 0 or 1, not continuous
