# 📈 Stock Market Prediction System

A full-stack AI-powered stock market prediction system that predicts stock price trends (Up/Down) using **LSTM** and **XGBoost** models with time-series forecasting.

![Python](https://img.shields.io/badge/Python-3.9+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green?logo=fastapi)
![React](https://img.shields.io/badge/React-18+-61DAFB?logo=react)
![TensorFlow](https://img.shields.io/badge/TensorFlow-2.x-orange?logo=tensorflow)

---

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   React Frontend│────▶│  FastAPI Backend │────▶│   ML Models     │
│   (Recharts,    │◀────│  (REST API)      │◀────│  (LSTM, XGBoost)│
│    TailwindCSS) │     │                  │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                              │
                              ▼
                        ┌─────────────┐
                        │  yfinance   │
                        │  (Live Data)│
                        └─────────────┘
```

## 📁 Project Structure

```
Project/
├── backend/                  # FastAPI backend server
│   ├── app/
│   │   ├── main.py          # FastAPI app entry point
│   │   ├── routes/
│   │   │   └── predict.py   # Prediction API routes
│   │   ├── services/
│   │   │   ├── data_service.py    # Stock data fetching
│   │   │   ├── feature_service.py # Feature engineering
│   │   │   └── model_service.py   # Model loading & inference
│   │   └── utils/
│   │       └── helpers.py   # Utility functions
│   ├── requirements.txt
│   └── .env.example
├── models/                   # ML model training & saved models
│   ├── train_lstm.py        # LSTM model training script
│   ├── train_xgboost.py     # XGBoost model training script
│   ├── evaluate.py          # Model evaluation & visualization
│   ├── feature_engineering.py # Feature engineering pipeline
│   ├── saved_models/        # Saved model weights
│   └── plots/               # Generated evaluation plots
├── datasets/                 # Dataset storage (upload here)
│   └── README.md            # Instructions for datasets
├── frontend/                 # React.js frontend
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── pages/           # Page components
│   │   ├── services/        # API service layer
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── tailwind.config.js
├── docs/                     # Documentation
│   └── DEPLOYMENT.md        # Deployment instructions
└── README.md                # This file
```

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+
- pip / conda

### 1. Train the Models

```bash
cd models
pip install -r ../backend/requirements.txt
python train_lstm.py
python train_xgboost.py
python evaluate.py
```

### 2. Start the Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API docs available at: http://localhost:8000/docs

### 3. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend available at: http://localhost:5173

## 🤖 Models

### LSTM (Long Short-Term Memory)
- Deep learning model for sequential time-series prediction
- Uses 60-day lookback window
- Features: SMA, EMA, RSI, MACD, Bollinger Bands, lag features
- Trained on scaled data with MinMaxScaler

### XGBoost (Gradient Boosting)
- Ensemble learning model for trend classification
- Binary classification: Up (1) / Down (0)
- Uses same engineered features as LSTM
- Provides probability-based confidence scores

## 📊 Features Engineered
| Feature | Description |
|---------|-------------|
| SMA_20, SMA_50 | Simple Moving Averages |
| EMA_12, EMA_26 | Exponential Moving Averages |
| RSI_14 | Relative Strength Index |
| MACD, Signal | MACD and Signal Line |
| BB_Upper, BB_Lower | Bollinger Bands |
| Lag_1 to Lag_5 | Lagged close prices |
| Daily_Return | Daily percentage return |
| Volatility | Rolling 20-day std dev |

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/predict` | Get prediction for a stock ticker |
| GET | `/api/health` | Health check |
| GET | `/api/history/{ticker}` | Get historical stock data |

### Example Request
```json
POST /api/predict
{
  "ticker": "AAPL",
  "period": "2y"
}
```

### Example Response
```json
{
  "ticker": "AAPL",
  "lstm_prediction": "Up",
  "lstm_confidence": 0.78,
  "xgboost_prediction": "Up",
  "xgboost_confidence": 0.82,
  "ensemble_prediction": "Up",
  "ensemble_confidence": 0.80,
  "current_price": 185.42,
  "forecast_prices": [186.1, 187.3, 188.0, 187.5, 189.2]
}
```

## 🚢 Deployment

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed deployment instructions.

| Component | Platform | Cost |
|-----------|----------|------|
| Frontend | Vercel / Netlify | Free |
| Backend | Render / Railway | Free tier |
| Models | Stored in backend | Included |

## 🔮 Future Improvements
- [ ] Sentiment analysis using news headlines (NLP)
- [ ] Twitter/X sentiment integration
- [ ] Backtesting module with historical performance
- [ ] Real-time WebSocket price updates
- [ ] Portfolio tracking and optimization
- [ ] Options pricing predictions

## 📝 License
This project is for educational purposes — AAI Semester 6 Project.
