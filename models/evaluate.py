"""
Model Evaluation & Comparison Script
======================================
Loads trained LSTM and XGBoost models, evaluates them on test data,
and generates comparison plots and a summary report.

Usage:
    python evaluate.py --ticker AAPL --period 5y
"""

import os
import sys
import json
import pickle
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import yfinance as yf
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, classification_report, roc_auc_score
)

import tensorflow as tf

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from feature_engineering import engineer_features, get_feature_columns

# Directories
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SAVED_MODELS_DIR = os.path.join(SCRIPT_DIR, "saved_models")
PLOTS_DIR = os.path.join(SCRIPT_DIR, "plots")
DATASETS_DIR = os.path.join(SCRIPT_DIR, "..", "datasets")

LOOKBACK = 60
TRAIN_SPLIT = 0.8


def load_models(ticker: str):
    """Load both trained models."""
    # Load LSTM
    lstm_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_lstm_model.keras")
    if os.path.exists(lstm_path):
        lstm_model = tf.keras.models.load_model(lstm_path)
        print(f"✅ LSTM model loaded from {lstm_path}")
    else:
        print(f"⚠️  LSTM model not found at {lstm_path}")
        lstm_model = None

    # Load XGBoost
    xgb_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_xgboost_model.pkl")
    if os.path.exists(xgb_path):
        with open(xgb_path, "rb") as f:
            xgb_model = pickle.load(f)
        print(f"✅ XGBoost model loaded from {xgb_path}")
    else:
        print(f"⚠️  XGBoost model not found at {xgb_path}")
        xgb_model = None

    return lstm_model, xgb_model


def prepare_data(ticker: str, period: str = "5y"):
    """Prepare data for evaluation."""
    cache_path = os.path.join(DATASETS_DIR, f"{ticker}_stock_data.csv")

    if os.path.exists(cache_path):
        df = pd.read_csv(cache_path, parse_dates=["Date"])
    else:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
        df.reset_index(inplace=True)

    featured_df = engineer_features(df, include_target=True)
    feature_cols = get_feature_columns()

    features = featured_df[feature_cols].values
    target = featured_df["Target"].values

    # Scale
    scaler = MinMaxScaler(feature_range=(0, 1))
    features_scaled = scaler.fit_transform(features)

    # Split
    split_idx = int(len(features) * TRAIN_SPLIT)

    return features, features_scaled, target, split_idx, feature_cols, featured_df


def evaluate_models(ticker: str = "AAPL", period: str = "5y"):
    """Evaluate and compare both models."""
    print("=" * 70)
    print(f"📊 Model Evaluation & Comparison — {ticker}")
    print("=" * 70)

    lstm_model, xgb_model = load_models(ticker)
    features, features_scaled, target, split_idx, feature_cols, featured_df = prepare_data(ticker, period)

    results = {}

    # ── LSTM Evaluation ───────────────────────────────────────────────
    if lstm_model is not None:
        print("\n── LSTM Evaluation ──")
        X_seq, y_seq = [], []
        for i in range(LOOKBACK, len(features_scaled)):
            X_seq.append(features_scaled[i - LOOKBACK:i])
            y_seq.append(target[i])
        X_seq, y_seq = np.array(X_seq), np.array(y_seq)

        split_seq = int(len(X_seq) * TRAIN_SPLIT)
        X_test_lstm = X_seq[split_seq:]
        y_test_lstm = y_seq[split_seq:]

        y_prob_lstm = lstm_model.predict(X_test_lstm, verbose=0).flatten()
        y_pred_lstm = (y_prob_lstm >= 0.5).astype(int)

        results["LSTM"] = {
            "accuracy": accuracy_score(y_test_lstm, y_pred_lstm),
            "precision": precision_score(y_test_lstm, y_pred_lstm, zero_division=0),
            "recall": recall_score(y_test_lstm, y_pred_lstm, zero_division=0),
            "f1": f1_score(y_test_lstm, y_pred_lstm, zero_division=0),
            "auc": roc_auc_score(y_test_lstm, y_prob_lstm) if len(np.unique(y_test_lstm)) > 1 else 0,
            "y_true": y_test_lstm,
            "y_pred": y_pred_lstm,
            "y_prob": y_prob_lstm,
        }

    # ── XGBoost Evaluation ────────────────────────────────────────────
    if xgb_model is not None:
        print("\n── XGBoost Evaluation ──")
        X_test_xgb = features[split_idx:]
        y_test_xgb = target[split_idx:]

        y_prob_xgb = xgb_model.predict_proba(X_test_xgb)[:, 1]
        y_pred_xgb = xgb_model.predict(X_test_xgb)

        results["XGBoost"] = {
            "accuracy": accuracy_score(y_test_xgb, y_pred_xgb),
            "precision": precision_score(y_test_xgb, y_pred_xgb, zero_division=0),
            "recall": recall_score(y_test_xgb, y_pred_xgb, zero_division=0),
            "f1": f1_score(y_test_xgb, y_pred_xgb, zero_division=0),
            "auc": roc_auc_score(y_test_xgb, y_prob_xgb) if len(np.unique(y_test_xgb)) > 1 else 0,
            "y_true": y_test_xgb,
            "y_pred": y_pred_xgb,
            "y_prob": y_prob_xgb,
        }

    # ── Ensemble (Average probabilities) ──────────────────────────────
    if lstm_model is not None and xgb_model is not None:
        print("\n── Ensemble Evaluation ──")
        # Align test sizes (LSTM has fewer due to lookback)
        min_len = min(len(y_prob_lstm), len(y_prob_xgb))
        y_prob_ens = (y_prob_lstm[-min_len:] + y_prob_xgb[-min_len:]) / 2
        y_pred_ens = (y_prob_ens >= 0.5).astype(int)
        y_true_ens = y_test_xgb[-min_len:]

        results["Ensemble"] = {
            "accuracy": accuracy_score(y_true_ens, y_pred_ens),
            "precision": precision_score(y_true_ens, y_pred_ens, zero_division=0),
            "recall": recall_score(y_true_ens, y_pred_ens, zero_division=0),
            "f1": f1_score(y_true_ens, y_pred_ens, zero_division=0),
            "auc": roc_auc_score(y_true_ens, y_prob_ens) if len(np.unique(y_true_ens)) > 1 else 0,
            "y_true": y_true_ens,
            "y_pred": y_pred_ens,
            "y_prob": y_prob_ens,
        }

    # ── Print comparison table ────────────────────────────────────────
    print(f"\n{'=' * 65}")
    print(f"{'Model':<12} {'Accuracy':>10} {'Precision':>10} {'Recall':>10} {'F1':>10} {'AUC':>10}")
    print(f"{'─' * 65}")
    for name, r in results.items():
        print(f"{name:<12} {r['accuracy']:>10.4f} {r['precision']:>10.4f} "
              f"{r['recall']:>10.4f} {r['f1']:>10.4f} {r['auc']:>10.4f}")
    print(f"{'=' * 65}")

    # ── Plot comparison ───────────────────────────────────────────────
    plot_comparison(results, ticker)

    # ── Save comparison results ───────────────────────────────────────
    comparison = {}
    for name, r in results.items():
        comparison[name] = {
            "accuracy": round(r["accuracy"], 4),
            "precision": round(r["precision"], 4),
            "recall": round(r["recall"], 4),
            "f1": round(r["f1"], 4),
            "auc": round(r["auc"], 4),
        }

    comp_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_comparison.json")
    with open(comp_path, "w") as f:
        json.dump(comparison, f, indent=2)
    print(f"\n💾 Comparison results saved to {comp_path}")

    return results


def plot_comparison(results: dict, ticker: str):
    """Generate comparison visualization."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    models = list(results.keys())
    metrics = ["accuracy", "precision", "recall", "f1", "auc"]
    colors = ["#667EEA", "#FF6B6B", "#4ECDC4", "#FFE66D", "#A8E6CF"]

    # Bar chart comparison
    x = np.arange(len(models))
    width = 0.15

    for i, metric in enumerate(metrics):
        values = [results[m][metric] for m in models]
        bars = axes[0].bar(x + i * width, values, width, label=metric.upper(),
                          color=colors[i], edgecolor="white", linewidth=0.5)
        for bar, val in zip(bars, values):
            axes[0].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.005,
                        f"{val:.3f}", ha="center", va="bottom", fontsize=7, fontweight="bold")

    axes[0].set_xticks(x + width * 2)
    axes[0].set_xticklabels(models, fontsize=11)
    axes[0].set_ylabel("Score", fontsize=12)
    axes[0].set_title(f"Model Comparison — {ticker}", fontsize=14, fontweight="bold")
    axes[0].legend(fontsize=9)
    axes[0].set_ylim(0, 1.1)
    axes[0].grid(True, axis="y", alpha=0.3)

    # Radar chart
    angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
    angles += angles[:1]

    model_colors = {"LSTM": "#667EEA", "XGBoost": "#FF6B6B", "Ensemble": "#4ECDC4"}

    ax_radar = fig.add_subplot(122, polar=True)
    for name in models:
        values = [results[name][m] for m in metrics]
        values += values[:1]
        color = model_colors.get(name, "#999")
        ax_radar.plot(angles, values, "o-", linewidth=2, label=name, color=color)
        ax_radar.fill(angles, values, alpha=0.1, color=color)

    ax_radar.set_xticks(angles[:-1])
    ax_radar.set_xticklabels([m.upper() for m in metrics], fontsize=9)
    ax_radar.set_ylim(0, 1)
    ax_radar.set_title(f"Model Radar — {ticker}", fontsize=14, fontweight="bold", pad=20)
    ax_radar.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1), fontsize=9)
    ax_radar.grid(True, alpha=0.3)

    # Remove the empty subplot
    axes[1].set_visible(False)

    plt.tight_layout()
    save_path = os.path.join(PLOTS_DIR, f"{ticker}_model_comparison.png")
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"📊 Comparison plot saved to {save_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate and compare models")
    parser.add_argument("--ticker", type=str, default="AAPL", help="Stock ticker symbol")
    parser.add_argument("--period", type=str, default="5y", help="Historical data period")
    args = parser.parse_args()

    results = evaluate_models(ticker=args.ticker, period=args.period)
