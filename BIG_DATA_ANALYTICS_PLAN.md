# Stock Market Analytics and Prediction Using Apache Spark

## Purpose and agreed scope

Extend the existing stock prediction application with a reproducible market-wide analytics pipeline that runs directly on macOS. Use Yahoo Finance through `yfinance` for historical data, local Parquet files for storage, and PySpark in local mode for processing. Present the results through the existing FastAPI backend and React frontend.

This document is an implementation plan. It does not indicate that any of the proposed features have been implemented.

### Constraints

- Run natively on the Mac: no virtual machine, Docker, Kafka, Hadoop cluster, or cloud deployment is required.
- Use historical daily data and batch processing for the first release.
- Keep the existing prediction feature working while adding a separate analytics workflow.
- Install analytics dependencies in their own environment rather than upgrading the existing ML dependencies together.
- Download and process data before the demo; the dashboard must work from saved results without internet access.
- Describe execution honestly as local Spark processing. Local worker threads are not a multi-machine cluster.

### What will make the project strong

The deliverable must show a documented dataset, reliable cleaning, useful market-wide analytics, verified calculations, and reproducible performance measurements. Installing Spark or reaching a particular row count alone does not establish a big data contribution. Check the course rubric before claiming that local execution satisfies a mandatory distributed-cluster requirement.

## 1. Existing application and proposed architecture

The repository already has React pages, a FastAPI prediction API, per-stock feature engineering, LSTM/XGBoost models, and Yahoo Finance fetching. `models/train_all.py` currently lists 24 stocks. These components provide the starting point.

```text
Configured stock universe
          |
Yahoo Finance / yfinance
          |
Resumable historical ingestion + download manifest
          |
Raw local files
          |
PySpark validation, deduplication, normalization
          |
Cleaned Parquet, partitioned by market and year
          |
PySpark rolling features and market-wide aggregations
          |
Versioned summary JSON + data-quality report
          |
FastAPI read-only analytics endpoints
          |
React Market Analytics page

Existing prediction routes and models remain available alongside analytics.
```

Spark runs only in command-line batch jobs. FastAPI serves compact saved summaries; it does not start Spark or ingest the full dataset for an HTTP request.

## 2. Dataset strategy

### Start small, then expand

1. Validate the entire workflow with 20 stocks and approximately two years of daily data.
2. Expand to 100 stocks and up to ten years where available.
3. Expand toward 500–1,000 stocks after measuring disk space, ingestion reliability, and processing time.

For illustration, 1,000 stocks multiplied by ten years and approximately 252 trading days is about 2.52 million daily records. Actual results depend on coverage, listing dates, failed downloads, and the configured universe. Publish actual counts rather than expected counts.

Use a checked-in ticker configuration with market and exchange information. A US-only initial analytics universe simplifies trading-calendar and currency comparisons; retain the existing application's Indian-stock prediction support. Adding NSE analytics is a later extension using the same schema.

### Data access

- Reuse `yfinance`; its standard documented workflow does not require an API key.
- Use a versioned ticker list with its source and retrieval date recorded. Do not imply a present-day stock list represents the historical investable universe.
- Download in small batches with bounded concurrency, retries, exponential backoff, and a resumable manifest. Respect provider access conditions and responses; do not attempt to bypass throttling.
- Record successful, failed, empty, and partial downloads separately. Missing or delisted symbols must not stop the whole run.
- Keep downloaded files available so rerunning analytics does not require another network download.
- Provide a local CSV import option using the same schema if Yahoo access is unavailable or an existing historical dataset offers better coverage.
- Do not add intraday ingestion to the first release. Historical availability and provider restrictions should be evaluated separately before that extension.

### Canonical daily schema

| Field | Meaning |
|---|---|
| `ticker` | Provider-qualified stock symbol |
| `market` | Market identifier, such as US or NSE |
| `exchange` | Exchange identifier where known |
| `currency` | Price currency |
| `date` | Trading-session date in the exchange's local calendar |
| `open`, `high`, `low`, `close` | Unadjusted OHLC prices |
| `adj_close` | Provider-supplied adjusted close, when available |
| `volume` | Reported share volume |
| `source`, `fetched_at` | Provenance and retrieval time |

Explicitly configure the download adjustment behavior rather than relying on a library default. Preserve raw OHLC and use adjusted close for comparable historical return calculations. If adjusted close is missing, flag that limitation rather than silently mixing price conventions.

### Storage and updates

- Save immutable raw ingestion batches and download manifests under `datasets/market/raw/`.
- Store validated data under `datasets/market/clean/market=US/year=2025/` and equivalent partitions.
- Avoid partitioning every ticker/date combination; compact output to prevent many tiny files.
- Deduplicate by `(market, exchange, ticker, date)` with a deterministic latest-ingestion rule.
- Make repeat ingestion idempotent: the same inputs must not increase unique record counts.
- Incremental ingestion should refetch an overlapping recent interval and merge affected partitions. Periodic full-history refreshes must account for corporate-action revisions to adjusted historical prices.
- Ignore environments, raw data, generated Parquet, and full analytics outputs in Git. Commit configuration, scripts, documentation, and a small sample fixture.

## 3. Environment and local execution

- Observed during planning: Apple Silicon Mac, Java 21, and default Python 3.15.1. Available memory was not established.
- Prefer a separate Python 3.11 environment for the initial analytics implementation; verify the chosen PySpark and data-library versions together and pin the working combination.
- Keep analytics requirements in `analytics/requirements.txt`. Do not install the old backend's full TensorFlow stack into this environment.
- Add only the packages needed for ingestion, Parquet interchange, Spark processing, and measurement: `yfinance`, `pandas`, `pyarrow`, `pyspark`, and optionally `psutil` for memory measurements.
- Start Spark with `local[2]` and a small configurable shuffle-partition count. Choose memory limits only after inspecting the machine; avoid assuming all CPU cores or memory are available.
- Provide one command for the small end-to-end demo and separate commands for ingestion, processing, and benchmarking.

Proposed command interface, to be implemented:

```bash
python -m analytics.cli demo
python -m analytics.cli ingest --universe analytics/config/universe.csv
python -m analytics.cli process
python -m analytics.cli benchmark
```

The demo command should use a small cached dataset after initial acquisition. Spark jobs run separately from the existing app startup.

## 4. Data quality and analytics

### Cleaning rules

- Enforce the schema and parse dates without shifting the exchange's trading date through UTC conversion.
- Reject or quarantine missing identifiers/dates, nonpositive prices, negative volume, inconsistent OHLC ranges, and malformed numeric values. Zero volume should be flagged and handled explicitly rather than automatically treated as an error.
- Deduplicate records and sort by stock and trading date before time-dependent calculations.
- Do not forward-fill nonexistent trading sessions or silently invent missing prices.
- Report input rows, accepted rows, duplicate rows, rejected rows, ticker coverage, date coverage, and rejection reasons.
- Validate each market separately and avoid comparing nominal prices or summing currency-denominated values across currencies without conversion.

### First-release calculations

| Metric | Definition and implementation rule |
|---|---|
| Daily return | Adjusted close divided by the previous valid session's adjusted close, minus one |
| Moving averages | 20- and 50-session averages of adjusted close within each stock |
| Rolling volatility | Sample standard deviation of daily returns over 20 sessions; label whether annualized |
| Volume ratio | Current volume divided by the mean volume of the previous 20 sessions, excluding the current session |
| Volume anomaly | Configurable ratio threshold, initially 2x; handle zero/missing baseline explicitly |
| Market breadth | Counts of positive, negative, and unchanged returns for a selected market/date |
| Rankings | Top gainers, losers, most volatile stocks, and volume anomalies for a selected date |

Require complete lookback windows before publishing rolling metrics. Windows must be partitioned by stock identity and ordered by date. Label missing-session gaps in quality reporting; do not describe a multi-session return as a reliable daily observation without checking continuity.

Persist cleaned and feature data as Parquet. Export only bounded, dashboard-ready summaries as JSON. Do not collect the full dataset into pandas or the API process.

Sector comparisons, correlations, news sentiment, streaming, and distributed model training are optional later work, not first-release requirements.

## 5. Backend and dashboard integration

### Backend

Add `backend/app/routes/analytics.py` and `backend/app/services/analytics_service.py`. Register the router in `backend/app/main.py`.

Proposed read-only endpoints:

| Endpoint | Response |
|---|---|
| `GET /api/analytics/overview` | Dataset coverage, latest available session, quality counts, pipeline status |
| `GET /api/analytics/rankings?market=US&date=...` | Bounded gainers, losers, volatility, and anomaly lists |
| `GET /api/analytics/stock/{ticker}?market=US&start=...&end=...` | Bounded price/indicator series exported by the batch job |
| `GET /api/analytics/benchmarks` | Saved benchmark results and execution environment |

Validate query parameters and cap response sizes. Export per-stock series files or another bounded lookup artifact so arbitrary history requests do not require reading the entire feature dataset. Use a run manifest to identify available symbols and dates.

Write new outputs to a versioned run directory and publish a small current-run manifest atomically only after validation succeeds. The API must read a consistent completed run, return a clear not-ready state before the first run, and expose the last successful run after a failed refresh. Include data and generation timestamps in responses.

### Frontend

- Add `frontend/src/pages/Analytics.jsx`, route `/analytics`, and a navigation link using the existing design and chart library.
- Show records processed, stocks covered, historical range, quality summary, and last successful refresh.
- Provide market/date controls, gainers and losers, volatility rankings, volume anomalies, and a selected-stock indicator chart.
- Include a benchmark comparison chart with dataset size, runtime, and hardware context.
- Provide loading, empty, stale-data, and error states. Default to a date actually present in the saved dataset.
- Label values as historical analytics; do not present saved summaries as a live feed.

Keep existing prediction behavior available. Scheduled model training and reading precomputed features into the ML pipeline can follow after the analytics release is stable.

## 6. Performance evidence and correctness

### Benchmark design

1. Use the same cleaned records and the same workload in pandas and PySpark: rolling stock features plus date-level rankings/aggregates.
2. Start with approximately 100,000 records, then 1 million, then the largest genuine dataset available. Do not fabricate coverage to reach a target.
3. Execute an actual output write or action so Spark's lazy computation is included.
4. Run implementations separately and repeat measured runs, reporting the median and variability. Separate Spark startup from processing time and state whether inputs are cached.
5. Record exact row counts, input/output bytes, runtime, throughput, software versions, hardware, thread count, and Spark settings.
6. Record memory only with a defined measurement method. Python-only process memory does not include the Spark JVM; report the process tree or identify that limitation.
7. Save raw measurements and generate dashboard/report artifacts. Report cases where Spark is slower or either implementation cannot complete.

Optional synthetic scaling runs must be clearly separate from real market results and must not be used as evidence of actual market coverage. A benchmark using replicated ticker identities must preserve meaningful window partitions rather than create duplicate sessions for the same stock.

### Meaningful validation

- Compare pandas and Spark returns, window alignment, sample volatility, and volume ratios on a deterministic multi-stock fixture with floating-point tolerances.
- Check duplicate ingestion, unavailable tickers, malformed rows, insufficient lookback, missing sessions, and corporate-action price handling.
- Confirm rerunning ingestion leaves unique counts unchanged and a failed publish preserves the previous complete dashboard snapshot.
- Confirm time-dependent features never use future observations. For any later ML integration, split chronologically and fit preprocessing on training data only.
- Check API validation/not-ready behavior and manually verify the dashboard against saved summaries.
- Run the frontend production build and the repository's relevant existing checks without introducing unrelated dependency changes.

## 7. Proposed repository additions

```text
analytics/
  __init__.py
  cli.py                  # Demo, ingestion, processing, benchmark commands
  requirements.txt        # Verified and pinned analytics dependencies
  config/universe.csv     # Ticker list, markets, exchanges, provenance
  ingest.py               # Yahoo downloads and CSV import
  pipeline.py             # Spark cleaning, features, summaries, publication
  benchmark.py            # Equivalent pandas/Spark workloads and measurements
  tests/                  # Small deterministic correctness fixtures/checks
datasets/market/          # Generated raw and cleaned data; Git-ignored
artifacts/analytics/      # Versioned summaries/manifests; bulk output Git-ignored
backend/app/routes/analytics.py
backend/app/services/analytics_service.py
frontend/src/pages/Analytics.jsx
docs/BIG_DATA_ANALYTICS.md
```

Also update `.gitignore`, backend router registration, frontend routes/navigation/API helpers, and the README. Add Makefile targets or equivalent shortcuts for the four analytics commands.

## 8. Implementation order and completion gates

| Phase | Deliverable | Gate before continuing |
|---|---|---|
| 1. Bootstrap | Isolated environment, pinned packages, local Spark smoke run | Read and write a tiny Parquet dataset successfully |
| 2. Ingest | 20-stock dataset, provenance, retries, resumability | A repeated run produces no duplicate stock sessions |
| 3. Process | Clean Parquet, quality report, calculated summaries | Spark calculations agree with the pandas fixture |
| 4. Integrate | Read-only endpoints and `/analytics` page | Dashboard works offline from a completed snapshot |
| 5. Scale | Expanded real dataset and benchmark artifacts | Counts, limits, failures, and timings are recorded |
| 6. Present | README, architecture, methodology, limitations, demo steps | A fresh small run can be reproduced from documentation |

Do not start by retraining every model or downloading the largest possible universe. Complete the small end-to-end workflow first and increase scale only after correctness and stability are established.

## 9. Final presentation and acceptance criteria

The demonstration should show:

1. The recorded source, stock universe, actual record count, and historical coverage.
2. A completed Spark job and its quality report.
3. Market-wide rankings, anomaly detection, and historical indicator charts.
4. The existing stock prediction feature.
5. Measured pandas/Spark results, configuration, and limitations.

Completion means the pipeline is repeatable, the calculations are verified, the dashboard serves saved results without downloading data, and no VM or external cluster is needed. The report must disclose historical-data gaps, present-day-universe survivorship bias, provider dependencies, and the difference between local parallel processing and multi-machine execution.

## References

- [yfinance documentation](https://ranaroussi.github.io/yfinance/): documented data access and usage context.
- [PySpark installation](https://spark.apache.org/docs/latest/api/python/getting_started/install.html): environment and dependency requirements; recheck when selecting pinned versions.
- [Spark local execution](https://spark.apache.org/docs/latest/submitting-applications.html): `local[K]` uses K local worker threads.
- [Spark Parquet support](https://spark.apache.org/docs/latest/sql-data-sources-parquet.html): storage and partition discovery.
