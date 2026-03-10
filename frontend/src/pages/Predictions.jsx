import { useState, useEffect, useCallback } from 'react'
import { AlertCircle, RefreshCw } from 'lucide-react'
import SearchBar from '../components/SearchBar'
import StockChart from '../components/StockChart'
import ForecastChart from '../components/ForecastChart'
import PredictionResults from '../components/PredictionResults'
import TrendingStocks from '../components/TrendingStocks'
import LoadingSkeleton from '../components/LoadingSkeleton'
import { predictStock, getStockHistory, getTrendingStocks } from '../services/api'

export default function Predictions() {
    const [ticker, setTicker] = useState('')
    const [market, setMarket] = useState('auto')
    const [predictionData, setPredictionData] = useState(null)
    const [chartData, setChartData] = useState(null)
    const [chartPeriod, setChartPeriod] = useState('1y')
    const [trending, setTrending] = useState([])
    const [isLoading, setIsLoading] = useState(false)
    const [isChartLoading, setIsChartLoading] = useState(false)
    const [error, setError] = useState(null)

    useEffect(() => {
        async function loadTrending() {
            try {
                const res = await getTrendingStocks()
                setTrending(res.trending || [])
            } catch (err) {
                console.warn('Could not load trending stocks:', err)
                setTrending([
                    { ticker: 'AAPL', name: 'Apple Inc.', sector: 'Technology', market: 'US' },
                    { ticker: 'GOOGL', name: 'Alphabet Inc.', sector: 'Technology', market: 'US' },
                    { ticker: 'MSFT', name: 'Microsoft Corp.', sector: 'Technology', market: 'US' },
                    { ticker: 'TSLA', name: 'Tesla Inc.', sector: 'Automotive', market: 'US' },
                    { ticker: 'NVDA', name: 'NVIDIA Corp.', sector: 'Technology', market: 'US' },
                    { ticker: 'RELIANCE.NS', name: 'Reliance Industries', sector: 'Energy', market: 'NSE' },
                    { ticker: 'TCS.NS', name: 'Tata Consultancy', sector: 'Technology', market: 'NSE' },
                    { ticker: 'INFY.NS', name: 'Infosys Ltd.', sector: 'Technology', market: 'NSE' },
                ])
            }
        }
        loadTrending()
    }, [])

    const handleSearch = useCallback(async (searchTicker, searchMarket = 'auto') => {
        const t = searchTicker.toUpperCase().trim()
        if (!t) return

        setTicker(t)
        setMarket(searchMarket)
        setIsLoading(true)
        setError(null)
        setPredictionData(null)
        setChartData(null)

        try {
            const [prediction, history] = await Promise.all([
                predictStock(t, '2y', searchMarket),
                getStockHistory(t, chartPeriod, searchMarket),
            ])
            setPredictionData(prediction)
            setChartData(history)

            // Update ticker to resolved version from backend
            if (prediction?.ticker) {
                setTicker(prediction.ticker)
            }
        } catch (err) {
            console.error('Prediction error:', err)
            const message = err.response?.data?.detail || err.message || 'Failed to fetch prediction'
            setError(message)
        } finally {
            setIsLoading(false)
        }
    }, [chartPeriod])

    const handlePeriodChange = useCallback(async (period) => {
        if (!ticker) return
        setChartPeriod(period)
        setIsChartLoading(true)

        try {
            const history = await getStockHistory(ticker, period, market)
            setChartData(history)
        } catch (err) {
            console.error('Chart period change error:', err)
        } finally {
            setIsChartLoading(false)
        }
    }, [ticker, market])

    return (
        <section style={{ paddingTop: '6rem', paddingBottom: '6rem', width: '100%' }}>
            <div className="section-wrapper" style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
                {/* Header */}
                <div style={{ textAlign: 'center', maxWidth: '36rem', marginLeft: 'auto', marginRight: 'auto' }}>
                    <h1 style={{
                        fontSize: '2rem',
                        fontWeight: 600,
                        letterSpacing: '-0.025em',
                        color: '#f1f5f9',
                        marginBottom: '0.75rem',
                    }}>
                        Stock Predictions
                    </h1>
                    <p style={{ fontSize: '1rem', color: '#94a3b8', lineHeight: 1.7 }}>
                        AI-powered trend predictions for <span style={{ color: '#818cf8', fontWeight: 500 }}>US</span> and <span style={{ color: '#f59e0b', fontWeight: 500 }}>Indian</span> stock markets.
                    </p>
                </div>

                {/* Search */}
                <div style={{ maxWidth: '36rem', marginLeft: 'auto', marginRight: 'auto', width: '100%' }}>
                    <SearchBar onSearch={handleSearch} isLoading={isLoading} />
                </div>

                {/* Error */}
                {error && (
                    <div style={{
                        background: 'rgba(244,63,94,0.08)',
                        border: '1px solid rgba(244,63,94,0.2)',
                        borderRadius: '0.75rem',
                        padding: '1rem 1.25rem',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '1rem',
                        maxWidth: '36rem',
                        marginLeft: 'auto',
                        marginRight: 'auto',
                    }}>
                        <AlertCircle size={20} style={{ color: '#f43f5e', flexShrink: 0 }} />
                        <div style={{ flex: 1 }}>
                            <h3 style={{ fontSize: '0.875rem', fontWeight: 500, color: '#fb7185' }}>Prediction Error</h3>
                            <p style={{ fontSize: '0.875rem', color: '#94a3b8', marginTop: '0.25rem' }}>{error}</p>
                        </div>
                        <button
                            onClick={() => handleSearch(ticker, market)}
                            style={{
                                padding: '0.5rem',
                                borderRadius: '0.5rem',
                                color: '#94a3b8',
                                background: 'transparent',
                                border: 'none',
                                cursor: 'pointer',
                            }}
                        >
                            <RefreshCw size={16} />
                        </button>
                    </div>
                )}

                {/* Loading */}
                {isLoading && <LoadingSkeleton />}

                {/* Results */}
                {!isLoading && predictionData && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', width: '100%' }}>
                        <PredictionResults data={predictionData} />
                        {predictionData?.forecast_prices?.length > 0 && (
                            <ForecastChart
                                forecast={predictionData.forecast_prices}
                                currentPrice={predictionData.current_price}
                                currency={predictionData.currency}
                                ticker={ticker}
                            />
                        )}
                        {chartData && (
                            <StockChart
                                data={chartData.data}
                                ticker={ticker}
                                onPeriodChange={handlePeriodChange}
                                activePeriod={chartPeriod}
                                currency={predictionData?.currency}
                            />
                        )}
                    </div>
                )}

                {/* Trending */}
                {!isLoading && !predictionData && (
                    <div style={{ paddingTop: '2rem', borderTop: '1px solid rgba(30,41,59,0.5)' }}>
                        <TrendingStocks
                            stocks={trending}
                            onSelect={handleSearch}
                            isLoading={isLoading}
                        />
                    </div>
                )}
            </div>
        </section>
    )
}
