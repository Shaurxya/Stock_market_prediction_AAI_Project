"""
LSTM Model Training Script — CORRECTED Version
=================================================
Fixes applied:
  1. Scaler fit ONLY on training data (no data leakage)
  2. Scaler params saved and reused consistently
  3. Sequence-target alignment fixed (include day i → predict i→i+1)
  4. Lighter architecture (~12K params vs ~250K) for small datasets
  5. Dropout reduced (0.15-0.2 vs 0.3)
  6. Unidirectional LSTM instead of Bidirectional (better for forecasting)
  7. Class weights for imbalanced up/down distribution
  8. ReduceLROnPlateau added alongside EarlyStopping
  9. BatchNormalization for training stability
  10. Proper evaluation with classification report

Usage:
    python train_lstm.py --ticker AAPL --period 5y --epochs 100
"""

import os
import sys
import json
import argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from datetime import datetime

import yfinance as yf
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, confusion_matrix, classification_report
)

import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
from tensorflow.keras.optimizers import Adam

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from feature_engineering import engineer_features, get_feature_columns

# ─── Configuration ───────────────────────────────────────────────────────
LOOKBACK = 60          # Number of past days to use for prediction
EPOCHS = 100           # Max training epochs
BATCH_SIZE = 32        # Training batch size
LEARNING_RATE = 0.001  # Initial learning rate
TRAIN_SPLIT = 0.8      # 80% train, 20% test
RANDOM_SEED = 42

# Reproducibility
np.random.seed(RANDOM_SEED)
tf.random.set_seed(RANDOM_SEED)

# Directories
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SAVED_MODELS_DIR = os.path.join(SCRIPT_DIR, "saved_models")
PLOTS_DIR = os.path.join(SCRIPT_DIR, "plots")
DATASETS_DIR = os.path.join(SCRIPT_DIR, "..", "datasets")

os.makedirs(SAVED_MODELS_DIR, exist_ok=True)
os.makedirs(PLOTS_DIR, exist_ok=True)
os.makedirs(DATASETS_DIR, exist_ok=True)


def fetch_stock_data(ticker: str, period: str = "5y") -> pd.DataFrame:
    """Download stock data from Yahoo Finance and cache it."""
    print(f"📥 Fetching data for {ticker} (period: {period})...")

    cache_path = os.path.join(DATASETS_DIR, f"{ticker}_stock_data.csv")

    if os.path.exists(cache_path):
        print(f"   Loading cached data from {cache_path}")
        df = pd.read_csv(cache_path, parse_dates=["Date"])
    else:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
        df.reset_index(inplace=True)
        df.to_csv(cache_path, index=False)
        print(f"   Saved data to {cache_path}")

    print(f"   Shape: {df.shape} | Date range: {df['Date'].min()} → {df['Date'].max()}")
    return df


def prepare_sequences(data: np.ndarray, target: np.ndarray, lookback: int = LOOKBACK):
    """
    Create sequences for LSTM input — CORRECTED alignment.

    For each position i (from lookback to len-1):
      X[i] = features from day [i-lookback+1, ..., i]  (includes day i)
      y[i] = target[i] = whether Close[i+1] > Close[i]

    This way the model sees features UP TO AND INCLUDING day i,
    and predicts whether the price goes up from day i to day i+1.

    Returns:
        X: shape (samples, lookback, features)
        y: shape (samples,)
    """
    X, y = [], []
    for i in range(lookback - 1, len(data) - 1):
        # Sequence: [i - lookback + 1, ..., i] → lookback rows ending at day i
        X.append(data[i - lookback + 1: i + 1])
        y.append(target[i])
    return np.array(X), np.array(y)


def build_lstm_model(input_shape: tuple, learning_rate: float = LEARNING_RATE) -> Sequential:
    """
    Build CORRECTED LSTM model architecture.

    Key fixes:
    - Unidirectional LSTM (not bidirectional — better for time-series forecasting)
    - Much lighter (32→16 units vs 128→64) — appropriate for ~300-500 samples
    - Lower dropout (0.15-0.2 vs 0.3)
    - BatchNormalization for training stability
    - Total params: ~12K vs ~250K
    """
    model = Sequential([
        # Layer 1: LSTM with return_sequences for stacking
        LSTM(32, return_sequences=True, input_shape=input_shape,
             recurrent_dropout=0.1, name="lstm_1"),
        BatchNormalization(name="bn_1"),
        Dropout(0.15, name="dropout_1"),

        # Layer 2: LSTM final hidden state
        LSTM(16, return_sequences=False,
             recurrent_dropout=0.1, name="lstm_2"),
        BatchNormalization(name="bn_2"),
        Dropout(0.15, name="dropout_2"),

        # Dense layers
        Dense(8, activation="relu", name="dense_1"),
        Dropout(0.1, name="dropout_3"),

        # Output: sigmoid for binary classification
        Dense(1, activation="sigmoid", name="output")
    ], name="StockLSTM_v2")

    model.compile(
        optimizer=Adam(learning_rate=learning_rate),
        loss="binary_crossentropy",
        metrics=["accuracy"]
    )

    return model


def compute_class_weights(y: np.ndarray) -> dict:
    """Compute class weights to handle up/down imbalance."""
    n_samples = len(y)
    n_up = y.sum()
    n_down = n_samples - n_up

    if n_up == 0 or n_down == 0:
        return {0: 1.0, 1: 1.0}

    weight_down = n_samples / (2.0 * n_down)
    weight_up = n_samples / (2.0 * n_up)

    print(f"   ⚖️ Class weights: Down={weight_down:.3f}, Up={weight_up:.3f}")
    print(f"      Distribution: Up={n_up} ({n_up/n_samples*100:.1f}%), "
          f"Down={n_down} ({n_down/n_samples*100:.1f}%)")
    return {0: weight_down, 1: weight_up}


def plot_training_history(history, save_path: str):
    """Plot and save training history."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    axes[0].plot(history.history["loss"], label="Train Loss", color="#FF6B6B", linewidth=2)
    axes[0].plot(history.history["val_loss"], label="Val Loss", color="#4ECDC4", linewidth=2)
    axes[0].set_title("Model Loss", fontsize=14, fontweight="bold")
    axes[0].set_xlabel("Epoch")
    axes[0].set_ylabel("Loss")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(history.history["accuracy"], label="Train Accuracy", color="#FF6B6B", linewidth=2)
    axes[1].plot(history.history["val_accuracy"], label="Val Accuracy", color="#4ECDC4", linewidth=2)
    axes[1].set_title("Model Accuracy", fontsize=14, fontweight="bold")
    axes[1].set_xlabel("Epoch")
    axes[1].set_ylabel("Accuracy")
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"📊 Training history plot saved to {save_path}")


def plot_predictions(y_true, y_pred, y_prob, save_path: str):
    """Plot prediction results with confusion matrix."""
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    axes[0].hist(y_prob, bins=50, color="#667EEA", alpha=0.7, edgecolor="white")
    axes[0].axvline(x=0.5, color="#FF6B6B", linestyle="--", linewidth=2, label="Threshold")
    axes[0].set_title("Prediction Probability Distribution", fontsize=12, fontweight="bold")
    axes[0].set_xlabel("Probability (Up)")
    axes[0].set_ylabel("Count")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    cm = confusion_matrix(y_true, y_pred)
    im = axes[1].imshow(cm, interpolation="nearest", cmap="Blues")
    axes[1].set_title("Confusion Matrix", fontsize=12, fontweight="bold")
    axes[1].set_xlabel("Predicted")
    axes[1].set_ylabel("Actual")
    axes[1].set_xticks([0, 1])
    axes[1].set_yticks([0, 1])
    axes[1].set_xticklabels(["Down", "Up"])
    axes[1].set_yticklabels(["Down", "Up"])
    for i in range(2):
        for j in range(2):
            axes[1].text(j, i, str(cm[i, j]), ha="center", va="center",
                        fontsize=16, fontweight="bold",
                        color="white" if cm[i, j] > cm.max() / 2 else "black")
    fig.colorbar(im, ax=axes[1])

    axes[2].plot(y_true[:100], label="Actual", color="#FF6B6B", alpha=0.7, linewidth=1.5)
    axes[2].plot(y_pred[:100], label="Predicted", color="#4ECDC4", alpha=0.7, linewidth=1.5, linestyle="--")
    axes[2].set_title("Actual vs Predicted (First 100)", fontsize=12, fontweight="bold")
    axes[2].set_xlabel("Sample")
    axes[2].set_ylabel("Trend (0=Down, 1=Up)")
    axes[2].legend()
    axes[2].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"📊 Prediction results plot saved to {save_path}")


def train_lstm(ticker: str = "AAPL", period: str = "5y", epochs: int = EPOCHS):
    """
    CORRECTED LSTM training pipeline.

    Fixes applied:
    1. Scaler fit ONLY on training portion (no data leakage)
    2. Sequence alignment: features[i-59:i+1] → target[i]
    3. Lighter architecture (~12K params)
    4. Class weights for imbalanced data
    5. ReduceLROnPlateau + EarlyStopping
    6. Proper debug logging throughout
    """
    print("=" * 70)
    print(f"🚀 LSTM Training Pipeline v2 (CORRECTED) — {ticker}")
    print(f"   Period: {period} | Epochs: {epochs} | Lookback: {LOOKBACK}")
    print("=" * 70)

    # ── Step 1: Fetch data ────────────────────────────────────────────
    df = fetch_stock_data(ticker, period)

    # ── Step 2: Engineer features + target ────────────────────────────
    featured_df = engineer_features(df, include_target=True)

    # ── Step 3: Prepare features and target ───────────────────────────
    feature_cols = get_feature_columns()
    features = featured_df[feature_cols].values
    target = featured_df["Target"].values

    print(f"\n📐 Features shape: {features.shape}")
    print(f"   Target distribution: Up={target.sum()}, Down={len(target) - target.sum()}")

    # ── Step 4: TRAIN/TEST SPLIT FIRST (before scaling!) ──────────────
    split_idx = int(len(features) * TRAIN_SPLIT)

    features_train_raw = features[:split_idx]
    features_test_raw = features[split_idx:]
    target_train_raw = target[:split_idx]
    target_test_raw = target[split_idx:]

    # ── Step 5: FIT SCALER ONLY ON TRAINING DATA ─────────────────────
    scaler = MinMaxScaler(feature_range=(0, 1))
    features_train_scaled = scaler.fit_transform(features_train_raw)  # FIT on train only
    features_test_scaled = scaler.transform(features_test_raw)        # TRANSFORM on test

    # Verify scaling ranges
    print(f"\n🔬 Scaler Diagnostics:")
    print(f"   Train scaled range: [{features_train_scaled.min():.4f}, {features_train_scaled.max():.4f}]")
    print(f"   Test scaled range:  [{features_test_scaled.min():.4f}, {features_test_scaled.max():.4f}]")

    # Check for NaN/Inf after scaling
    if np.any(np.isnan(features_train_scaled)) or np.any(np.isinf(features_train_scaled)):
        print("   ⚠️ WARNING: NaN or Inf detected in scaled training data!")
        # Replace NaN/Inf
        features_train_scaled = np.nan_to_num(features_train_scaled, nan=0.0, posinf=1.0, neginf=0.0)
        features_test_scaled = np.nan_to_num(features_test_scaled, nan=0.0, posinf=1.0, neginf=0.0)

    # Save scaler parameters
    scaler_params = {
        "min_": scaler.min_.tolist(),
        "scale_": scaler.scale_.tolist(),
        "data_min_": scaler.data_min_.tolist(),
        "data_max_": scaler.data_max_.tolist(),
        "feature_columns": feature_cols,
        "fit_on": "training_data_only",
    }
    scaler_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_scaler_params.json")
    with open(scaler_path, "w") as f:
        json.dump(scaler_params, f, indent=2)
    print(f"💾 Scaler parameters saved to {scaler_path}")

    # ── Step 6: Create sequences from train and test SEPARATELY ──────
    X_train, y_train = prepare_sequences(features_train_scaled, target_train_raw, LOOKBACK)
    X_test, y_test = prepare_sequences(features_test_scaled, target_test_raw, LOOKBACK)

    print(f"\n📦 Sequence shapes:")
    print(f"   X_train: {X_train.shape}, y_train: {y_train.shape}")
    print(f"   X_test:  {X_test.shape}, y_test:  {y_test.shape}")

    if len(X_train) < 50:
        print("   ❌ Too few training sequences! Need at least 50.")
        print("   💡 Try a longer period (e.g., --period 5y or --period 10y)")
        return None, None, None

    # ── Step 7: Debug — verify target distribution in sequences ──────
    print(f"\n🔬 Debug — Target distribution in sequences:")
    print(f"   Train: Up={y_train.sum()}/{len(y_train)} ({y_train.mean()*100:.1f}%)")
    print(f"   Test:  Up={y_test.sum()}/{len(y_test)} ({y_test.mean()*100:.1f}%)")

    # ── Step 8: Compute class weights ────────────────────────────────
    class_weights = compute_class_weights(y_train)

    # ── Step 9: Build model ──────────────────────────────────────────
    model = build_lstm_model(input_shape=(X_train.shape[1], X_train.shape[2]))
    model.summary()

    total_params = model.count_params()
    samples_per_param = len(X_train) / total_params
    print(f"\n📊 Model complexity check:")
    print(f"   Total params: {total_params:,}")
    print(f"   Training samples: {len(X_train)}")
    print(f"   Samples/param ratio: {samples_per_param:.2f} (want > 10)")
    if samples_per_param < 5:
        print("   ⚠️ Low samples/param ratio — model may overfit!")

    # ── Step 10: Callbacks ───────────────────────────────────────────
    model_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_lstm_model.keras")
    callbacks = [
        EarlyStopping(
            monitor="val_loss",
            patience=15,
            restore_best_weights=True,
            verbose=1
        ),
        ModelCheckpoint(
            model_path,
            monitor="val_loss",
            save_best_only=True,
            verbose=1
        ),
        ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.5,
            patience=5,
            min_lr=1e-6,
            verbose=1
        ),
    ]

    # ── Step 11: Train ───────────────────────────────────────────────
    print("\n🏋️ Training LSTM model...")
    history = model.fit(
        X_train, y_train,
        validation_data=(X_test, y_test),
        epochs=epochs,
        batch_size=BATCH_SIZE,
        callbacks=callbacks,
        class_weight=class_weights,
        verbose=1
    )

    # ── Step 12: Evaluate ────────────────────────────────────────────
    print("\n📊 Evaluating model...")
    y_prob = model.predict(X_test, verbose=0).flatten()
    y_pred = (y_prob >= 0.5).astype(int)

    # Debug: check prediction distribution
    print(f"\n🔬 Prediction diagnostics:")
    print(f"   Probability range: [{y_prob.min():.4f}, {y_prob.max():.4f}]")
    print(f"   Probability mean:  {y_prob.mean():.4f}")
    print(f"   Probability std:   {y_prob.std():.4f}")
    print(f"   Predicted Up: {y_pred.sum()}/{len(y_pred)} ({y_pred.mean()*100:.1f}%)")

    if y_prob.std() < 0.05:
        print("   ⚠️ WARNING: Predictions are nearly constant — model may not be learning!")

    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)

    print(f"\n{'─' * 40}")
    print(f"📈 LSTM v2 Results for {ticker}")
    print(f"{'─' * 40}")
    print(f"   Accuracy:  {accuracy:.4f} ({accuracy * 100:.2f}%)")
    print(f"   Precision: {precision:.4f}")
    print(f"   Recall:    {recall:.4f}")
    print(f"   F1 Score:  {f1:.4f}")
    print(f"{'─' * 40}")
    print(f"\n{classification_report(y_test, y_pred, target_names=['Down', 'Up'])}")

    # ── Step 13: Save results ────────────────────────────────────────
    results = {
        "ticker": ticker,
        "model_type": "LSTM_v2",
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "train_samples": int(X_train.shape[0]),
        "test_samples": int(X_test.shape[0]),
        "lookback": LOOKBACK,
        "epochs_trained": len(history.history["loss"]),
        "best_val_loss": round(min(history.history["val_loss"]), 4),
        "total_params": total_params,
        "samples_per_param": round(samples_per_param, 2),
        "prediction_std": round(float(y_prob.std()), 4),
        "feature_columns": feature_cols,
        "trained_at": datetime.now().isoformat(),
        "scaler_fit": "training_data_only",
        "fixes_applied": [
            "scaler_on_train_only",
            "sequence_alignment_fixed",
            "lighter_architecture",
            "class_weights",
            "reduce_lr_on_plateau",
            "batch_normalization",
        ],
    }

    results_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_lstm_results.json")
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"💾 Results saved to {results_path}")

    # ── Step 14: Plot results ────────────────────────────────────────
    plot_training_history(
        history, os.path.join(PLOTS_DIR, f"{ticker}_lstm_training_history.png")
    )
    plot_predictions(
        y_test, y_pred, y_prob,
        os.path.join(PLOTS_DIR, f"{ticker}_lstm_predictions.png")
    )

    print(f"\n✅ LSTM v2 training complete! Model saved to {model_path}")
    return model, scaler, results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train LSTM v2 model for stock prediction")
    parser.add_argument("--ticker", type=str, default="AAPL", help="Stock ticker symbol")
    parser.add_argument("--period", type=str, default="5y", help="Historical data period")
    parser.add_argument("--epochs", type=int, default=EPOCHS, help="Number of training epochs")
    args = parser.parse_args()

    model, scaler, results = train_lstm(
        ticker=args.ticker,
        period=args.period,
        epochs=args.epochs
    )
