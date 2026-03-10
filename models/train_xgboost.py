"""
XGBoost Model Training Script for Stock Market Prediction
==========================================================
Trains an XGBoost classifier for binary trend prediction (Up/Down).
Uses the same feature engineering pipeline as the LSTM model.

Usage:
    python train_xgboost.py --ticker AAPL --period 5y
"""

import os
import sys
import json
import pickle
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

import yfinance as yf
import xgboost as xgb
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import TimeSeriesSplit, GridSearchCV
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, confusion_matrix, classification_report,
    roc_auc_score, roc_curve
)

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from feature_engineering import engineer_features, get_feature_columns

# ─── Configuration ───────────────────────────────────────────────────────
TRAIN_SPLIT = 0.8
RANDOM_SEED = 42

np.random.seed(RANDOM_SEED)

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


def plot_feature_importance(model, feature_names, save_path: str, top_n: int = 15):
    """Plot top N most important features."""
    importance = model.feature_importances_
    indices = np.argsort(importance)[::-1][:top_n]

    fig, ax = plt.subplots(figsize=(10, 6))
    colors = plt.cm.viridis(np.linspace(0.3, 0.9, top_n))

    ax.barh(
        range(top_n),
        importance[indices][::-1],
        color=colors,
        edgecolor="white",
        linewidth=0.5
    )
    ax.set_yticks(range(top_n))
    ax.set_yticklabels([feature_names[i] for i in indices[::-1]], fontsize=10)
    ax.set_xlabel("Feature Importance", fontsize=12)
    ax.set_title("XGBoost — Top Feature Importances", fontsize=14, fontweight="bold")
    ax.grid(True, axis="x", alpha=0.3)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"📊 Feature importance plot saved to {save_path}")


def plot_roc_curve(y_true, y_prob, save_path: str):
    """Plot ROC curve with AUC score."""
    fpr, tpr, thresholds = roc_curve(y_true, y_prob)
    auc_score = roc_auc_score(y_true, y_prob)

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot(fpr, tpr, color="#667EEA", linewidth=2.5,
            label=f"ROC Curve (AUC = {auc_score:.4f})")
    ax.plot([0, 1], [0, 1], color="#FF6B6B", linestyle="--", linewidth=1.5,
            label="Random Classifier")
    ax.fill_between(fpr, tpr, alpha=0.1, color="#667EEA")

    ax.set_xlabel("False Positive Rate", fontsize=12)
    ax.set_ylabel("True Positive Rate", fontsize=12)
    ax.set_title("XGBoost — ROC Curve", fontsize=14, fontweight="bold")
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"📊 ROC curve saved to {save_path}")


def plot_xgb_predictions(y_true, y_pred, y_prob, save_path: str):
    """Plot XGBoost prediction analysis."""
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    # Probability distribution
    axes[0].hist(y_prob[y_true == 1], bins=40, alpha=0.6, color="#4ECDC4",
                 label="Actual Up", edgecolor="white")
    axes[0].hist(y_prob[y_true == 0], bins=40, alpha=0.6, color="#FF6B6B",
                 label="Actual Down", edgecolor="white")
    axes[0].axvline(x=0.5, color="black", linestyle="--", linewidth=1.5)
    axes[0].set_title("Probability by Actual Class", fontsize=12, fontweight="bold")
    axes[0].set_xlabel("Predicted Probability (Up)")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # Confusion Matrix
    cm = confusion_matrix(y_true, y_pred)
    im = axes[1].imshow(cm, interpolation="nearest", cmap="Purples")
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

    # Rolling accuracy
    window = 20
    rolling_correct = pd.Series((y_true == y_pred).astype(int)).rolling(window).mean()
    axes[2].plot(rolling_correct, color="#667EEA", linewidth=1.5)
    axes[2].axhline(y=0.5, color="#FF6B6B", linestyle="--", linewidth=1, alpha=0.7)
    axes[2].set_title(f"Rolling Accuracy (Window={window})", fontsize=12, fontweight="bold")
    axes[2].set_xlabel("Sample")
    axes[2].set_ylabel("Accuracy")
    axes[2].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"📊 Prediction analysis plot saved to {save_path}")


def train_xgboost(ticker: str = "AAPL", period: str = "5y", tune: bool = False):
    """
    Main training pipeline for XGBoost model.

    Steps:
    1. Fetch stock data
    2. Engineer features
    3. Train/test split (time-series aware)
    4. Train XGBoost classifier
    5. Evaluate and save model
    """
    print("=" * 70)
    print(f"🚀 XGBoost Training Pipeline — {ticker}")
    print(f"   Period: {period} | Hyperparameter Tuning: {tune}")
    print("=" * 70)

    # ── Step 1: Fetch data ────────────────────────────────────────────
    df = fetch_stock_data(ticker, period)

    # ── Step 2: Engineer features ─────────────────────────────────────
    featured_df = engineer_features(df, include_target=True)

    # ── Step 3: Prepare features and target ───────────────────────────
    feature_cols = get_feature_columns()
    X = featured_df[feature_cols].values
    y = featured_df["Target"].values

    print(f"\n📐 Features shape: {X.shape}")
    print(f"   Target distribution: Up={y.sum()}, Down={len(y) - y.sum()}")
    print(f"   Baseline accuracy: {max(y.mean(), 1 - y.mean()):.4f}")

    # ── Step 4: Train/test split (chronological) ──────────────────────
    split_idx = int(len(X) * TRAIN_SPLIT)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    print(f"   Train: {X_train.shape[0]} samples")
    print(f"   Test:  {X_test.shape[0]} samples")

    # ── Step 5: Define model ──────────────────────────────────────────
    if tune:
        print("\n🔍 Running hyperparameter tuning...")
        param_grid = {
            "n_estimators": [100, 200, 300],
            "max_depth": [3, 5, 7],
            "learning_rate": [0.01, 0.05, 0.1],
            "subsample": [0.8, 0.9, 1.0],
            "colsample_bytree": [0.8, 0.9, 1.0],
        }

        base_model = xgb.XGBClassifier(
            objective="binary:logistic",
            eval_metric="logloss",
            random_state=RANDOM_SEED,
            use_label_encoder=False,
        )

        tscv = TimeSeriesSplit(n_splits=3)
        grid = GridSearchCV(
            base_model, param_grid,
            cv=tscv, scoring="accuracy",
            n_jobs=-1, verbose=1
        )
        grid.fit(X_train, y_train)
        model = grid.best_estimator_
        print(f"   Best params: {grid.best_params_}")
        print(f"   Best CV score: {grid.best_score_:.4f}")

    else:
        model = xgb.XGBClassifier(
            n_estimators=200,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            min_child_weight=3,
            gamma=0.1,
            reg_alpha=0.1,
            reg_lambda=1.0,
            objective="binary:logistic",
            eval_metric="logloss",
            random_state=RANDOM_SEED,
            use_label_encoder=False,
        )

    # ── Step 6: Train ─────────────────────────────────────────────────
    print("\n🏋️ Training XGBoost model...")
    model.fit(
        X_train, y_train,
        eval_set=[(X_train, y_train), (X_test, y_test)],
        verbose=20
    )

    # ── Step 7: Evaluate ──────────────────────────────────────────────
    print("\n📊 Evaluating model...")
    y_prob = model.predict_proba(X_test)[:, 1]
    y_pred = model.predict(X_test)

    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    auc = roc_auc_score(y_test, y_prob)

    print(f"\n{'─' * 40}")
    print(f"📈 XGBoost Model Results for {ticker}")
    print(f"{'─' * 40}")
    print(f"   Accuracy:  {accuracy:.4f} ({accuracy * 100:.2f}%)")
    print(f"   Precision: {precision:.4f}")
    print(f"   Recall:    {recall:.4f}")
    print(f"   F1 Score:  {f1:.4f}")
    print(f"   ROC AUC:   {auc:.4f}")
    print(f"{'─' * 40}")
    print(f"\n{classification_report(y_test, y_pred, target_names=['Down', 'Up'])}")

    # ── Step 8: Save model ────────────────────────────────────────────
    model_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_xgboost_model.pkl")
    with open(model_path, "wb") as f:
        pickle.dump(model, f)
    print(f"💾 Model saved to {model_path}")

    # Save results
    results = {
        "ticker": ticker,
        "model_type": "XGBoost",
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "roc_auc": round(auc, 4),
        "train_samples": int(X_train.shape[0]),
        "test_samples": int(X_test.shape[0]),
        "feature_columns": feature_cols,
        "model_params": model.get_params(),
        "trained_at": datetime.now().isoformat(),
    }

    results_path = os.path.join(SAVED_MODELS_DIR, f"{ticker}_xgboost_results.json")
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"💾 Results saved to {results_path}")

    # ── Step 9: Plot results ──────────────────────────────────────────
    plot_feature_importance(
        model, feature_cols,
        os.path.join(PLOTS_DIR, f"{ticker}_xgb_feature_importance.png")
    )
    plot_roc_curve(
        y_test, y_prob,
        os.path.join(PLOTS_DIR, f"{ticker}_xgb_roc_curve.png")
    )
    plot_xgb_predictions(
        y_test, y_pred, y_prob,
        os.path.join(PLOTS_DIR, f"{ticker}_xgb_predictions.png")
    )

    print(f"\n✅ XGBoost training complete! Model saved to {model_path}")
    return model, results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train XGBoost model for stock prediction")
    parser.add_argument("--ticker", type=str, default="AAPL", help="Stock ticker symbol")
    parser.add_argument("--period", type=str, default="5y", help="Historical data period")
    parser.add_argument("--tune", action="store_true", help="Enable hyperparameter tuning")
    args = parser.parse_args()

    model, results = train_xgboost(
        ticker=args.ticker,
        period=args.period,
        tune=args.tune
    )
