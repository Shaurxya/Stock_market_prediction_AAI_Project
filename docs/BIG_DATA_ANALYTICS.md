# Local Spark market analytics

This implements the historical batch workflow in `BIG_DATA_ANALYTICS_PLAN.md`. The existing home, prediction, history, US/NSE/BSE selection, charts and about page remain available. Analytics is a separate page at `/analytics` and never starts Spark inside FastAPI.

## Install and run on macOS

Use Python 3.11, Java 21 and Node 18+ (Node 22 LTS recommended). The verified analytics combination is pinned in `analytics/requirements.txt`: Spark 4.0.1, pandas 2.2.3, NumPy 1.26.4, PyArrow 19.0.1, yfinance 1.4.1 and psutil 7.0.0. Spark uses Java 17+; Java 21 was exercised here. Backend ML dependencies remain in their existing separate environment.

```bash
# macOS prerequisites if missing:
brew install python@3.11 openjdk@21 libomp

make install
make analytics-install

# First acquisition: first 20 configured stocks, about two years.
# Includes ingestion, Spark processing and three-repeat benchmarks.
make analytics-demo

# Start website and API; no Spark process is started by this command.
npm start
```

Open `http://localhost:5173/analytics`, `http://localhost:5173/predict` and `http://localhost:8000/docs`. If a port is occupied, startup reports it without killing other applications. On this machine the prerequisites and both environments have been installed and a full snapshot already exists; `npm start` is enough after stopping any previously running app servers.

After acquisition, the dashboard reads local JSON without Yahoo or Spark. To reproduce processing and benchmarks without internet access:

```bash
make analytics-demo ARGS="--offline"
```

The offline command uses **all** saved raw batches in the chosen data root. To keep the 20-stock demonstration separate after expanding, use the same alternate `--data-root` and `--artifacts-root` on every command; point the backend at that artifacts directory with `ANALYTICS_ARTIFACTS_DIR`.

## Command reference

Run these from the repository root. `--end` is exclusive. The initial universe is a versioned, manually curated 100-symbol US watchlist; see `analytics/config/README.md` for its provenance and limitations.

```bash
# Acquire all 100 configured symbols, up to ten years where available.
make analytics-ingest ARGS="--start 2016-10-27 --end 2026-10-27"
make analytics-process

# Refresh recent overlap (10 calendar days) and new sessions.
make analytics-ingest ARGS="--start 2016-10-27 --end 2026-10-28 --incremental"
make analytics-process

# Periodic complete history refresh for corporate-action revisions.
make analytics-ingest ARGS="--start 2016-10-27 --end 2026-10-28 --refresh"

# Import an existing canonical CSV. No provider access required.
analytics/.venv/bin/python -m analytics.cli import-csv /path/to/history.csv
make analytics-process

# Benchmarks on a real subset and the full available dataset.
make analytics-benchmark ARGS="--max-rows 100000 --repeats 3"
make analytics-benchmark ARGS="--repeats 3"

# All command options:
analytics/.venv/bin/python -m analytics.cli --help
analytics/.venv/bin/python -m analytics.cli ingest --help
```

Processing defaults to `local[2]` and four shuffle partitions. `--master local[1]`, `local[2]` or `local[4]`, `--partitions N` and `--anomaly-threshold 2` are configurable. The verified machine has eight logical CPUs and 8 GiB RAM. No all-core default, large driver-memory reservation, VM, Docker, Hadoop service or cloud account is needed.

Yahoo acquisition has at most two concurrent downloads by default (configurable 1–4), three attempts and bounded exponential backoff. A manifest checkpoints completed symbols, with `success`, `partial`, `empty`, `failed` and reused `cached` statuses. Partial includes limited listing history or missing adjusted-close coverage, not just transport failure. Retries respect provider responses; no throttle bypass is implemented. Repeating a completed request reuses successful local files. CSV content hashes make repeated imports idempotent.

The downloader's metadata date is a trading session in the exchange's local calendar; it does not convert session dates through UTC. `auto_adjust=False` preserves unadjusted provider OHLC and separately stores adjusted close. The existing prediction downloader explicitly uses its previous adjusted-OHLC convention (`auto_adjust=True`). Analytics does not alter prediction data inputs.

## Data and calculation rules

CSV columns, in header order:

```text
ticker,market,exchange,currency,date,open,high,low,close,adj_close,volume,source,fetched_at
```

Use ISO session dates (`YYYY-MM-DD`), an ISO retrieval timestamp, provider-qualified symbols, and nonempty source/exchange values. The supported market/currency pairs are US/USD, NSE/INR and BSE/INR. `adj_close` may be blank; it is never silently replaced with raw close. The tiny checked-in CSV under `analytics/tests/fixtures/` is explicitly synthetic test data, never real market coverage or a default dashboard dataset.

Spark rejects missing/malformed identifiers, dates, provenance, currency mismatches, nonfinite or nonpositive prices, negative/fractional/malformed volume and inconsistent OHLC. Invalid rows are written to quarantine with reasons. Zero volume and missing adjusted close are accepted but counted. A row can have several rejection reasons, so reason counts can exceed rejected-row counts. Accepted + duplicates + rejected always equals input rows.

Deduplication uses `(market, exchange, ticker, date)`, newest `fetched_at`, then a stable canonical row hash for deterministic ties. Raw input is immutable. Each run rebuilds a deduplicated compact snapshot, including overlap revisions. This full snapshot rebuild is intentional for the first local release; partition-selective incremental processing is not implemented. It trades additional IO for straightforward idempotence and atomic recovery. Newer raw batches and prior snapshots are retained until explicitly archived by the operator.

| Indicator | Definition |
|---|---|
| Session return | adjusted close / previous adjusted close − 1 |
| MA20 / MA50 | mean adjusted close over 20 / 50 stock observations, only with complete nonnull windows |
| Volatility20 | sample standard deviation (`ddof=1`) of 20 valid session returns, not annualized |
| Volume ratio | current volume / mean volume of the **previous** 20 observations, excluding current; missing for zero baseline |
| Anomaly | volume ratio ≥ configured threshold (default 2×); unavailable without a valid baseline |
| Breadth | positive, negative, unchanged and unavailable returns per market/session |

No price or nonexistent session is forward-filled. Continuity uses the union of observed sessions for each exchange and additionally flags gaps over seven calendar days. A stock missing an observed exchange session gets an unavailable return on the next observation. Missing adjusted close also suppresses adjacent returns. This method cannot detect a session absent for the entire exchange universe and is not an authoritative exchange holiday calendar. That limitation is exposed in the quality report. Price moving averages and volume windows count available stock observations; they do not invent values across gaps.

Rankings contain at most ten positive gainers, negative losers, volatile stocks and qualifying volume anomalies per market/date. Each row retains its price currency. Cross-currency nominal-price/turnover totals are not computed. Per-stock exports retain at most 3,000 sessions; date rankings also retain the latest 3,000 market sessions. The API returns at most 3,000 stock observations, with truncation and available-range metadata. Each stock lookup reads its hashed JSON artifact, never the full Parquet dataset.

## Storage and atomic publication

```text
datasets/market/
  raw/<batch>/                  # immutable CSV + acquisition/import manifest
  clean/<run>/market=US/year=*/  # compact validated Parquet
  features/<run>/market=US/year=*/
  quarantine/<run>/             # rejected rows and reasons
artifacts/analytics/
  runs/<run>/
    manifest.json
    overview.json
    quality.json
    rankings/US/<date>.json
    stocks/<hash>.json
  current.json                 # atomic pointer to a validated completed snapshot
  status.json                  # latest attempted refresh status
  benchmarks/<measurement>/    # raw timings, logs, outputs, report
  benchmark-current.json
```

A writer lock prevents overlapping pipeline publishers. The pipeline validates counts, breadth and bounded exports before atomically replacing `current.json`. Failed refreshes leave the last complete run available, with failure status exposed in overview. There is no automatic fallback to an unfinished or fabricated snapshot. A `503` with `not_ready` is returned before first publication. The frontend pins requests to its overview run ID so a concurrently published refresh cannot mix series and rankings from different runs.

Generated environments, raw data, Parquet and full output snapshots are Git-ignored. Small test fixtures, configuration, source code and the measured report under `docs/` are checked in. Do not delete previous run directories while clients may still be using pinned IDs. Snapshot disk use grows with retained runs; archive old versions deliberately. Moving a dashboard snapshot is sufficient for API serving; rerunning benchmarks after moving the whole project requires reprocessing to refresh the local Parquet paths in its run manifest.

## Read-only API

| Route | Parameters |
|---|---|
| `/api/analytics/overview` | completed-run coverage, quality, stocks, sessions, status and generation time |
| `/api/analytics/rankings` | `market=US`, optional `date=YYYY-MM-DD`, `limit=1..10`, optional `run` |
| `/api/analytics/stock/{ticker}` | `market=US`, optional inclusive `start`, `end`, `limit=1..3000`, optional `run` |
| `/api/analytics/benchmarks` | optional `run`; results must match the dataset run |

Malformed dates/markets/limits and reversed ranges return `422`; unavailable symbols/sessions return `404`. Saved-series requests outside a stock's coverage return an empty series. A snapshot older than seven days is flagged stale; a generation timestamp alone does not mean current market data. The reload button only rereads saved results; batch acquisition/processing stays in the CLI.

## Correctness and performance evidence

```bash
make analytics-test  # Spark vs pandas and publication/ingestion checks
make check           # prediction/API regressions and frontend production build
```

The deterministic multi-stock fixture checks adjusted corporate-action returns, complete lookback windows, sample volatility, the prior-only volume denominator, zero baselines, missing sessions/adjusted prices and absence of future observations. Other checks exercise malformed data, latest-ingestion deduplication, unavailable tickers, repeated imports, failed-publication recovery, API not-ready/query bounds, existing prediction routes, chronological training and unique forecast weekdays. Only the small fixture is collected into pandas for test comparisons; production processing streams bounded exports from Spark.

Benchmark workers run separately in fresh processes, with engine startup/import timing reported separately. Both implementations read the same cleaned records, compute the same rolling features, market/date breadth and top-ten return ranks, and materialize Parquet outputs. Spark's feature cache is populated inside the measured processing interval. Repeated runs report all raw timings, median, min/max, standard deviation, throughput, input/output sizes, versions, hardware and thread settings. Optional real subsets are materialized once, outside measurements, ordered by stock identity/date. OS caches are not cleared. Memory is the sum of worker and recursive-child RSS sampled every 100 ms, including the JVM; shared pages may be counted twice and short peaks missed.

See `docs/BIG_DATA_RESULTS.json` for measured runs on this machine. The available genuine dataset is approximately 247,000 rows. A one-million-row run is not claimed; scale by expanding a documented real universe after evaluating provider reliability, disk and memory. No symbol replication or synthetic scaling evidence is mixed into the report. Local Spark may be slower at this size; report that result as measured. Local worker threads are not multiple machines. A mandatory course requirement for a distributed cluster still needs a separate rubric check.

## Existing prediction fixes and limits

The prediction runtime keeps XGBoost on demand, optional background LSTM, model caching, US/Indian ticker resolution and its response format. Corrections exclude the unlabeled newest training row, purge the chronological train/test boundary label, include historical context for LSTM test sequences, keep the test set out of early stopping, replace the incompatible legacy Keras optimizer, handle flat-price RSI, and produce unique sequential forecast weekdays. Short history requests such as `1mo` no longer fail the old 50-row download gate. Network fetching runs outside FastAPI's event loop; TensorFlow imports/training run in its background executor, with one LSTM training job at a time. A force-retrain request bypasses both memory and disk caches.

Model metadata prevents an older Keras file being paired with a newly trained scaler. Pending LSTM work resumes when a cached XGBoost model is requested after a restart. A queued job cannot overwrite a newer model generation. The prediction UI also ignores stale search/history responses when the user changes stocks quickly.

Heuristic fallback is labeled and no longer impersonates two trained models. Monte Carlo price paths are labeled simulations, and forecast dates do not claim an exchange-holiday calendar. Live acquisition still depends on Yahoo availability. An LSTM may be weak or nearly constant; successful training proves the flow works, not that it has predictive skill. Probabilities are not calibrated guarantees. `MODEL_DIR` can select a separate writable cache; checked-in historical models remain available.

## Source documentation

- [PySpark 4.0.1 installation](https://spark.apache.org/docs/4.0.1/api/python/getting_started/install.html)
- [Spark SQL window semantics](https://spark.apache.org/docs/4.0.1/sql-ref-syntax-qry-select-window.html)
- [yfinance download and adjustment parameters](https://ranaroussi.github.io/yfinance/reference/api/yfinance.download.html)

Yahoo historical data access has provider terms and usage limits. The configured watchlist has survivorship/selection bias, missing/delisted symbols and incomplete listing histories. The local research dashboard discloses these limits rather than claiming complete market coverage or reliable investment recommendations.
