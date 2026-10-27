import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Activity, ArrowUpRight, Database, Layers, RefreshCw, ShieldCheck, Clock, AlertCircle } from 'lucide-react'
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, BarChart, Bar } from 'recharts'
import { getAnalyticsOverview, getAnalyticsRankings, getAnalyticsStock, getAnalyticsBenchmarks } from '../services/api'
import './Analytics.css'

const number = value => value == null ? '—' : Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 })
const percent = value => value == null ? '—' : `${(value * 100).toFixed(2)}%`
const message = error => {
    const detail = error.response?.data?.detail
    return typeof detail === 'string' ? detail : detail?.message || error.message || 'Unable to load saved analytics.'
}
const tooltip = { backgroundColor: '#111827', border: '1px solid #334155', borderRadius: 8, color: '#e2e8f0' }

function State({ children, error = false }) {
    return <div className={`analytics-state ${error ? 'analytics-error' : ''}`} role={error ? 'alert' : 'status'}>{children}</div>
}

function Ranking({ title, subtitle, rows, metric, format, selected, onSelect, tone }) {
    return <article className="card analytics-ranking">
        <div className="analytics-card-head"><h2>{title}</h2><span className={tone}>{subtitle}</span></div>
        {rows.length ? <table><thead><tr><th>Stock</th><th>{metric === 'daily_return' ? 'Return' : metric === 'volume_ratio' ? 'Ratio' : 'Volatility'}</th></tr></thead>
            <tbody>{rows.map(row => <tr key={`${row.exchange}:${row.ticker}`} className={selected === row.ticker ? 'analytics-selected' : ''}>
                <td><button type="button" onClick={() => onSelect(row.ticker)} aria-label={`View ${row.ticker} indicators`}>{row.ticker}<ArrowUpRight size={12} /></button>
                    <small>{row.exchange} · {row.currency}</small></td><td className={tone}>{format(row[metric])}</td>
            </tr>)}</tbody></table> : <p className="analytics-empty">No qualifying stocks for this session.</p>}
    </article>
}

export default function Analytics() {
    const [overview, setOverview] = useState(null)
    const [rankings, setRankings] = useState(null)
    const [series, setSeries] = useState(null)
    const [benchmarks, setBenchmarks] = useState(null)
    const [market, setMarket] = useState('')
    const [session, setSession] = useState('')
    const [ticker, setTicker] = useState('')
    const [refresh, setRefresh] = useState(0)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState('')
    const [rankError, setRankError] = useState('')
    const [seriesError, setSeriesError] = useState('')
    const [benchmarkError, setBenchmarkError] = useState('')
    const [range, setRange] = useState(252)

    useEffect(() => {
        const controller = new AbortController()
        setLoading(true); setError('')
        getAnalyticsOverview(controller.signal).then(data => {
            if (controller.signal.aborted) return
            setOverview(data)
            const first = Object.keys(data.markets)[0]
            setMarket(first); setSession(data.markets[first].dates.at(-1))
            setTicker(data.stocks.find(stock => stock.market === first)?.ticker || '')
        }).catch(err => { if (!controller.signal.aborted) setError(message(err)) })
            .finally(() => { if (!controller.signal.aborted) setLoading(false) })
        return () => controller.abort()
    }, [refresh])

    useEffect(() => {
        if (!overview || !market || !session) return
        const controller = new AbortController()
        setRankings(null); setRankError('')
        getAnalyticsRankings({ market, date: session, run: overview.run_id }, controller.signal)
            .then(data => { if (!controller.signal.aborted) setRankings(data) })
            .catch(err => { if (!controller.signal.aborted) setRankError(message(err)) })
        return () => controller.abort()
    }, [overview, market, session])

    useEffect(() => {
        if (!overview || !market || !ticker || !session) return
        const controller = new AbortController()
        setSeries(null); setSeriesError('')
        getAnalyticsStock(ticker, { market, end: session, limit: range, run: overview.run_id }, controller.signal)
            .then(data => { if (!controller.signal.aborted) setSeries(data) })
            .catch(err => { if (!controller.signal.aborted) setSeriesError(message(err)) })
        return () => controller.abort()
    }, [overview, market, ticker, session, range])

    useEffect(() => {
        if (!overview) return
        const controller = new AbortController()
        setBenchmarks(null); setBenchmarkError('')
        getAnalyticsBenchmarks(overview.run_id, controller.signal)
            .then(data => { if (!controller.signal.aborted) setBenchmarks(data) })
            .catch(err => { if (!controller.signal.aborted) setBenchmarkError(message(err)) })
        return () => controller.abort()
    }, [overview])

    const changeMarket = value => {
        setMarket(value); setSession(overview.markets[value].dates.at(-1))
        setTicker(overview.stocks.find(stock => stock.market === value)?.ticker || '')
    }
    const stocks = overview?.stocks.filter(stock => stock.market === market) || []
    const breadth = rankings?.breadth
    const last = series?.data.at(-1)
    const failures = overview?.pipeline.status === 'failed'
    const quality = overview?.quality
    const benchmarkRows = benchmarks?.summaries?.filter(row => row.median_seconds != null) || []
    const comparisonRows = benchmarks?.comparisons?.map(measurement => ({
        records: number(measurement.dataset_rows), ...Object.fromEntries(measurement.summaries.map(row => [row.engine, row.median_seconds])),
    })) || []

    return <section className="section-wrapper analytics-page">
        <header className="analytics-header">
            <div><div className="analytics-eyebrow"><Activity size={14} /> MARKET RESEARCH / HISTORICAL</div>
                <h1>Market Analytics</h1><p>A wider view of the market. Built from saved daily sessions with Apache Spark.</p></div>
            <button className="analytics-button" onClick={() => setRefresh(value => value + 1)} disabled={loading}><RefreshCw size={15} className={loading ? 'analytics-spin' : ''} /> Reload snapshot</button>
        </header>
        {loading ? <State><div className="spinner" /> Loading completed snapshot…</State>
            : error ? <State error><AlertCircle size={22} /><div><strong>Analytics unavailable</strong><p>{error}</p></div><button className="analytics-button" onClick={() => setRefresh(value => value + 1)}>Try again</button></State>
                : overview && <>
                    <div className={`analytics-notice ${overview.stale || failures ? 'analytics-warning' : ''}`}>
                        <Clock size={16} /><span>Historical snapshot · Data through <strong>{overview.data_as_of}</strong> · Generated {new Date(overview.generated_at).toLocaleString()}
                            {overview.stale && ' · Older than 7 days'}{failures && ' · Latest refresh failed; showing last successful run'}
                            {overview.pipeline.status === 'running' && ' · A new batch is processing'}</span>
                        <span className="analytics-tag">{overview.execution.mode}</span>
                    </div>
                    <div className="analytics-stats">
                        {[{ icon: Database, label: 'Validated records', value: number(overview.records), detail: `${number(quality.input_rows)} raw rows inspected` },
                            { icon: Layers, label: 'Stocks covered', value: number(overview.stocks_count), detail: `${Object.keys(overview.markets).length} market(s) · curated universe` },
                            { icon: Clock, label: 'Historical coverage', value: overview.date_range.start, detail: `through ${overview.date_range.end}` },
                            { icon: ShieldCheck, label: 'Data quality', value: `${number(quality.rejected_rows)} rejected`, detail: `${number(quality.duplicate_rows)} duplicates removed` }]
                            .map(({ icon: Icon, label, value, detail }) => <article className="card analytics-stat" key={label}><div><span>{label}</span><Icon size={17} /></div><strong>{value}</strong><small>{detail}</small></article>)}
                    </div>
                    {!!overview.acquisition?.failed_tickers.length && <p className="analytics-caption" style={{ marginTop: -20, marginBottom: 24 }}>
                        Provider coverage: {overview.acquisition.configured_stocks} configured symbols · Unavailable: {overview.acquisition.failed_tickers.join(', ')}
                        {!!overview.acquisition.partial_tickers.length && ` · Partial history: ${overview.acquisition.partial_tickers.join(', ')}`}
                    </p>}
                    <div className="analytics-toolbar"><div><span className="analytics-eyebrow">SESSION EXPLORER</span><h2>Market pulse</h2></div>
                        <div className="analytics-controls"><label>Market<select value={market} onChange={e => changeMarket(e.target.value)}>{Object.keys(overview.markets).map(value => <option key={value}>{value}</option>)}</select></label>
                            <label>Trading session<select value={session} onChange={e => setSession(e.target.value)}>{[...overview.markets[market].dates].reverse().map(value => <option key={value}>{value}</option>)}</select></label></div>
                    </div>
                    {rankError ? <State error>{rankError}</State> : !rankings ? <State>Loading session rankings…</State> : <>
                        <article className="card analytics-breadth"><div><h2>Market breadth</h2><p>{number(breadth.stocks)} stocks in this saved session</p></div>
                            <div className="analytics-breadth-values"><span className="analytics-positive">↑ {breadth.advancing} advancing</span><span className="analytics-negative">↓ {breadth.declining} declining</span><span>{breadth.unchanged} unchanged</span><span>{breadth.unavailable} unavailable</span></div>
                            <div className="analytics-breadth-bar" aria-label={`${breadth.advancing} advancing, ${breadth.declining} declining`}>
                                {[['advancing', '#10b981'], ['declining', '#f43f5e'], ['unchanged', '#64748b'], ['unavailable', '#334155']].map(([key, color]) => <span key={key} style={{ width: `${100 * breadth[key] / Math.max(1, breadth.stocks)}%`, background: color }} />)}</div>
                        </article>
                        <div className="analytics-rankings">
                            <Ranking title="Top gainers" subtitle="ADJUSTED RETURN" rows={rankings.gainers} metric="daily_return" format={percent} tone="analytics-positive" selected={ticker} onSelect={setTicker} />
                            <Ranking title="Top losers" subtitle="ADJUSTED RETURN" rows={rankings.losers} metric="daily_return" format={percent} tone="analytics-negative" selected={ticker} onSelect={setTicker} />
                            <Ranking title="Most volatile" subtitle="20 SESSIONS" rows={rankings.volatile} metric="volatility_20" format={percent} selected={ticker} onSelect={setTicker} />
                            <Ranking title="Volume anomalies" subtitle={`≥ ${overview.methodology.anomaly_threshold}× BASELINE`} rows={rankings.anomalies} metric="volume_ratio" format={value => `${number(value)}×`} selected={ticker} onSelect={setTicker} />
                        </div>
                    </>}
                    <article className="card analytics-chart-card">
                        <div className="analytics-toolbar"><div><span className="analytics-eyebrow">STOCK DEEP DIVE</span><h2>Price & indicators</h2></div><div className="analytics-controls">
                            <label>Stock<select value={ticker} onChange={e => setTicker(e.target.value)}>{stocks.map(stock => <option key={stock.ticker}>{stock.ticker}</option>)}</select></label>
                            <label>Lookback<select value={range} onChange={e => setRange(Number(e.target.value))}><option value={63}>63 sessions</option><option value={252}>252 sessions</option><option value={3000}>All saved sessions</option></select></label></div></div>
                        {seriesError ? <State error>{seriesError}</State> : !series ? <State>Loading indicators…</State> : !series.data.length ? <State>No saved prices for this stock on or before the selected session.</State> : <>
                            <div className="analytics-indicators"><span><small>Adjusted close · {series.currency}</small><strong>{number(last.adj_close)}</strong></span><span><small>Session return</small><strong className={last.daily_return >= 0 ? 'analytics-positive' : 'analytics-negative'}>{percent(last.daily_return)}</strong></span><span><small>20-session volatility</small><strong>{percent(last.volatility_20)}</strong></span><span><small>Volume ratio</small><strong>{last.volume_ratio == null ? '—' : `${number(last.volume_ratio)}×`}</strong></span>
                                <Link to="/predict" className="analytics-predict-link">Open predictions <ArrowUpRight size={15} /></Link></div>
                            <div className="analytics-chart" role="img" aria-label={`${ticker} adjusted historical prices and moving averages in ${series.currency}`}><ResponsiveContainer width="100%" height="100%"><LineChart data={series.data} margin={{ top: 12, right: 12, left: 0, bottom: 0 }}>
                                <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" vertical={false} /><XAxis dataKey="date" stroke="#94a3b8" minTickGap={55} tick={{ fontSize: 11 }} /><YAxis domain={['auto', 'auto']} stroke="#94a3b8" width={65} tick={{ fontSize: 11 }} tickFormatter={number} />
                                <Tooltip contentStyle={tooltip} formatter={number} /><Legend wrapperStyle={{ fontSize: 12 }} /><Line type="monotone" dataKey="adj_close" name="Adjusted close" stroke="#818cf8" dot={false} strokeWidth={2} isAnimationActive={false} />
                                <Line type="monotone" dataKey="sma_20" name="20-session MA" stroke="#34d399" dot={false} isAnimationActive={false} /><Line type="monotone" dataKey="sma_50" name="50-session MA" stroke="#fbbf24" dot={false} isAnimationActive={false} />
                            </LineChart></ResponsiveContainer></div>
                            <p className="analytics-caption">{series.data[0].date} — {last.date} · {series.data.length} sessions · Gaps and incomplete windows remain blank. Volatility is a sample standard deviation, not annualized.</p>
                        </>}
                    </article>
                    <div className="analytics-lower-grid"><article className="card analytics-chart-card"><div className="analytics-card-head"><h2>Processing benchmark</h2><span>MEASURED LOCALLY</span></div>
                        {benchmarkError ? <State error>{benchmarkError}</State> : !benchmarks ? <State>Loading measurements…</State> : benchmarks.status !== 'ready' ? <State>No benchmark measurements for this snapshot yet.</State> : <>
                            <p className="analytics-caption">{number(benchmarks.dataset_rows)} genuine records · {benchmarks.environment.architecture} · {benchmarks.environment.logical_cpus} logical CPUs · {number(benchmarks.environment.ram_bytes / 1024 ** 3)} GiB RAM · {benchmarks.environment.spark_master}</p>
                            {benchmarkRows.length ? <div className="analytics-benchmark-chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={comparisonRows.length ? comparisonRows : [{ records: number(benchmarks.dataset_rows), ...Object.fromEntries(benchmarkRows.map(row => [row.engine, row.median_seconds])) }]}><CartesianGrid stroke="#1e293b" vertical={false} /><XAxis dataKey="records" stroke="#94a3b8" tick={{ fontSize: 11 }} /><YAxis stroke="#94a3b8" unit="s" /><Tooltip contentStyle={tooltip} formatter={value => `${number(value)} seconds`} labelFormatter={label => `${label} genuine records`} /><Legend wrapperStyle={{ fontSize: 11 }} /><Bar dataKey="pandas" name="pandas median" fill="#34d399" radius={[5, 5, 0, 0]} /><Bar dataKey="spark" name="Spark median" fill="#818cf8" radius={[5, 5, 0, 0]} /></BarChart></ResponsiveContainer></div> : <State>No successful measurements; inspect the batch logs.</State>}
                            <table className="analytics-benchmark-table"><thead><tr><th>Engine</th><th>Runs</th><th>Min–max</th><th>Startup</th></tr></thead><tbody>{benchmarks.summaries.map(row => <tr key={row.engine}><td>{row.engine}</td><td>{row.completed_runs}/{row.requested_runs}</td><td>{number(row.min_seconds)}–{number(row.max_seconds)}s</td><td>{number(row.median_startup_seconds)}s</td></tr>)}</tbody></table>
                            <details><summary>Measurement method & environment</summary><p>{benchmarks.methodology}</p><p>{benchmarks.memory_method}</p><p>Python {benchmarks.environment.python} · Spark {benchmarks.environment.versions.pyspark} · pandas {benchmarks.environment.versions.pandas} · {benchmarks.environment.shuffle_partitions} shuffle partitions</p></details>
                        </>}</article>
                        <article className="card analytics-chart-card"><div className="analytics-card-head"><h2>Quality & methodology</h2><ShieldCheck size={17} /></div>
                            <dl className="analytics-quality">{[['Accepted', quality.accepted_rows], ['Duplicates removed', quality.duplicate_rows], ['Rejected', quality.rejected_rows], ['Missing adjusted close', quality.missing_adjusted_close], ['Zero-volume sessions', quality.zero_volume], ['Observed session gaps', quality.observed_session_gaps], ['Long calendar gaps', quality.long_calendar_gaps]].map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{number(value)}</dd></div>)}</dl>
                            {!!Object.keys(quality.rejection_reasons).length && <p className="analytics-caption">Rejections: {Object.entries(quality.rejection_reasons).map(([reason, count]) => `${reason.replaceAll('_', ' ')} (${count})`).join(', ')}. One row can have multiple reasons.</p>}
                            <details><summary>Calculation rules & limitations</summary><p>{quality.calendar_method}</p><p>Adjusted close drives returns and moving averages. Volume baselines use the previous 20 sessions. Complete windows are required.</p>{overview.limitations.map(value => <p key={value}>{value}</p>)}</details>
                            <p className="analytics-caption">Sources: {overview.sources.join(', ')} · {overview.execution.engine} {overview.execution.spark_version} · Batch {number(overview.execution.runtime_seconds)}s</p>
                        </article></div>
                </>}
    </section>
}
