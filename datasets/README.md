# 📊 Datasets Directory

## Overview
This folder is for storing stock market datasets used for model training.

## Option 1: Auto-Download via yfinance (Recommended)
The training scripts can automatically download stock data from Yahoo Finance.
No manual dataset upload needed — just run the training scripts.

## Option 2: Upload Custom Datasets
If you have custom CSV datasets, place them here with the following format:

### Expected CSV Format
```csv
Date,Open,High,Low,Close,Adj Close,Volume
2020-01-02,296.24,300.60,295.12,300.35,297.43,33870100
2020-01-03,297.15,300.58,296.50,297.43,294.54,36580700
...
```

### Required Columns
| Column | Type | Description |
|--------|------|-------------|
| Date | datetime | Trading date |
| Open | float | Opening price |
| High | float | Day's high price |
| Low | float | Day's low price |
| Close | float | Closing price |
| Adj Close | float | Adjusted close price |
| Volume | int | Trading volume |

### Naming Convention
Name your files as: `{TICKER}_stock_data.csv`  
Example: `AAPL_stock_data.csv`, `GOOGL_stock_data.csv`

## Recommended Datasets
- **AAPL** (Apple Inc.) – High liquidity, good for testing
- **GOOGL** (Alphabet) – Tech sector benchmark
- **MSFT** (Microsoft) – Stable blue-chip stock
- **TSLA** (Tesla) – High volatility, challenging prediction
- **SPY** (S&P 500 ETF) – Market index tracking

## Data Sources
- [Yahoo Finance](https://finance.yahoo.com/)
- [Alpha Vantage](https://www.alphavantage.co/)
- [Kaggle Stock Datasets](https://www.kaggle.com/datasets?search=stock+market)
