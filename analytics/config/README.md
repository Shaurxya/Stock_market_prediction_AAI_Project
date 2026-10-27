# Universe v1

`universe.csv` is a manually curated research watchlist of 100 US provider symbols, recorded on 2026-10-27. It is not an index constituent list and is not a historical investable universe. `recorded_at` is the configuration date, not a claim that an authoritative exchange listing was retrieved that day. Source URLs identify the provider instrument pages; acquisition manifests record actual retrieval times and availability.

The first 20 entries form the small demo. `--limit` takes the first N; omit it for all 100. Add provider-qualified symbols with market, exchange, currency and provenance before expanding. Entries must be unique by market/ticker. The supported market/currency pairs are US/USD, NSE/INR and BSE/INR. Indian prediction support is independent of this US analytics watchlist.

Missing, renamed or delisted symbols remain failed-download evidence. Initial acquisition found MMC unavailable and shorter histories for ABNB and CRWD. This is recorded rather than silently replacing symbols. Yahoo can revise availability and adjusted prices; your run is authoritative for its own counts.
