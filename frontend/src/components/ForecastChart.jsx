import { useMemo } from 'react'
import {
    AreaChart, Area, XAxis, YAxis, CartesianGrid,
    Tooltip, ResponsiveContainer, ReferenceLine
} from 'recharts'
import { TrendingUp, TrendingDown, Calendar, Target } from 'lucide-react'

function ForecastTooltip({ active, payload, label, currencySymbol = '$' }) {
    if (!active || !payload?.length) return null
    const d = payload[0]?.payload

    return (
        <div style={{
            background: '#111827',
            border: '1px solid rgba(129,140,248,0.2)',
            borderRadius: '10px',
            padding: '12px 16px',
            minWidth: '180px',
            boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
        }}>
            <p style={{ fontSize: '0.75rem', marginBottom: '0.5rem', color: '#818cf8', fontWeight: 600 }}>
                Day {d?.day} — {label}
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1.5rem' }}>
                    <span style={{ fontSize: '0.75rem', color: '#64748b' }}>Predicted</span>
                    <span style={{ fontSize: '0.875rem', fontWeight: 700, color: '#f1f5f9', fontFamily: 'var(--font-mono)' }}>
                        {currencySymbol}{d?.price?.toFixed(2)}
                    </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1.5rem' }}>
                    <span style={{ fontSize: '0.75rem', color: '#34d399' }}>High Est.</span>
                    <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#34d399', fontFamily: 'var(--font-mono)' }}>
                        {currencySymbol}{d?.high?.toFixed(2)}
                    </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1.5rem' }}>
                    <span style={{ fontSize: '0.75rem', color: '#fb7185' }}>Low Est.</span>
                    <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#fb7185', fontFamily: 'var(--font-mono)' }}>
                        {currencySymbol}{d?.low?.toFixed(2)}
                    </span>
                </div>
            </div>
        </div>
    )
}

export default function ForecastChart({ forecast, currentPrice, currency, ticker }) {
    const currencySymbol = currency === 'INR' ? '₹' : '$'

    const chartData = useMemo(() => {
        if (!forecast?.length) return []

        // Add "Today" as the first point
        const today = [
            {
                day: 0,
                date: 'Today',
                price: currentPrice,
                high: currentPrice,
                low: currentPrice,
            }
        ]

        return [...today, ...forecast.map(f => ({
            ...f,
            // Confidence band for the area between high and low
            band: [f.low, f.high],
        }))]
    }, [forecast, currentPrice])

    const stats = useMemo(() => {
        if (!forecast?.length) return null

        const lastDay = forecast[forecast.length - 1]
        const change = lastDay.price - currentPrice
        const changePercent = (change / currentPrice) * 100
        const maxHigh = Math.max(...forecast.map(f => f.high))
        const minLow = Math.min(...forecast.map(f => f.low))

        return {
            endPrice: lastDay.price,
            change,
            changePercent,
            isUp: change >= 0,
            maxHigh,
            minLow,
            range: maxHigh - minLow,
        }
    }, [forecast, currentPrice])

    if (!chartData.length || !stats) return null

    const lineColor = stats.isUp ? '#10b981' : '#f43f5e'
    const bandColor = stats.isUp ? '#10b981' : '#f43f5e'

    return (
        <div className="card fade-in-up" style={{ padding: '1.5rem' }}>
            {/* Header */}
            <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'flex-start', justifyContent: 'space-between', gap: '1rem', marginBottom: '1.5rem' }}>
                <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                        <Calendar size={15} style={{ color: '#818cf8' }} />
                        <span style={{ fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.1em', color: '#818cf8' }}>
                            30-Day Price Forecast
                        </span>
                    </div>
                    <h3 style={{ fontSize: '1.125rem', fontWeight: 600, color: '#f1f5f9' }}>
                        {ticker} — Projected Performance
                    </h3>
                    <p style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '0.25rem' }}>
                        Monte Carlo simulation with technical indicators
                    </p>
                </div>

                {/* Summary Stats */}
                <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                    <div style={{
                        background: stats.isUp ? 'rgba(16,185,129,0.08)' : 'rgba(244,63,94,0.08)',
                        border: `1px solid ${stats.isUp ? 'rgba(16,185,129,0.2)' : 'rgba(244,63,94,0.2)'}`,
                        borderRadius: '0.75rem',
                        padding: '0.75rem 1rem',
                        textAlign: 'center',
                        minWidth: '120px',
                    }}>
                        <p style={{ fontSize: '0.625rem', fontWeight: 500, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Day 30 Target</p>
                        <p style={{ fontSize: '1.25rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: stats.isUp ? '#10b981' : '#f43f5e' }}>
                            {currencySymbol}{stats.endPrice.toFixed(2)}
                        </p>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.25rem', marginTop: '0.25rem' }}>
                            {stats.isUp ? <TrendingUp size={12} color="#10b981" /> : <TrendingDown size={12} color="#f43f5e" />}
                            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: stats.isUp ? '#34d399' : '#fb7185', fontFamily: 'var(--font-mono)' }}>
                                {stats.isUp ? '+' : ''}{stats.changePercent.toFixed(2)}%
                            </span>
                        </div>
                    </div>

                    <div style={{
                        background: 'rgba(30,41,59,0.5)',
                        border: '1px solid #1e293b',
                        borderRadius: '0.75rem',
                        padding: '0.75rem 1rem',
                        textAlign: 'center',
                        minWidth: '100px',
                    }}>
                        <p style={{ fontSize: '0.625rem', fontWeight: 500, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Range</p>
                        <p style={{ fontSize: '0.8rem', fontWeight: 600, fontFamily: 'var(--font-mono)', color: '#34d399' }}>
                            {currencySymbol}{stats.maxHigh.toFixed(2)}
                        </p>
                        <p style={{ fontSize: '0.8rem', fontWeight: 600, fontFamily: 'var(--font-mono)', color: '#fb7185' }}>
                            {currencySymbol}{stats.minLow.toFixed(2)}
                        </p>
                    </div>
                </div>
            </div>

            {/* Chart */}
            <div style={{ width: '100%', height: 360 }}>
                <ResponsiveContainer>
                    <AreaChart data={chartData} margin={{ top: 10, right: 10, bottom: 5, left: 10 }}>
                        <defs>
                            <linearGradient id="forecastGradient" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stopColor={lineColor} stopOpacity={0.2} />
                                <stop offset="95%" stopColor={lineColor} stopOpacity={0} />
                            </linearGradient>
                            <linearGradient id="bandGradient" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stopColor={bandColor} stopOpacity={0.08} />
                                <stop offset="100%" stopColor={bandColor} stopOpacity={0.02} />
                            </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                        <XAxis
                            dataKey="date"
                            tick={{ fontSize: 10, fill: '#64748b' }}
                            tickLine={false}
                            axisLine={{ stroke: '#1e293b' }}
                            interval={4}
                            tickFormatter={(val) => {
                                if (val === 'Today') return 'Today'
                                const d = new Date(val)
                                return `${d.getDate()}/${d.getMonth() + 1}`
                            }}
                        />
                        <YAxis
                            tick={{ fontSize: 11, fill: '#64748b' }}
                            tickLine={false}
                            axisLine={false}
                            domain={['auto', 'auto']}
                            tickFormatter={(val) => `${currencySymbol}${val}`}
                            width={70}
                        />
                        <Tooltip content={<ForecastTooltip currencySymbol={currencySymbol} />} />

                        {/* Confidence band: High */}
                        <Area
                            type="monotone"
                            dataKey="high"
                            name="High Estimate"
                            stroke="none"
                            fill="url(#bandGradient)"
                            dot={false}
                        />
                        {/* Confidence band: Low */}
                        <Area
                            type="monotone"
                            dataKey="low"
                            name="Low Estimate"
                            stroke="none"
                            fill="#0B0F19"
                            dot={false}
                        />

                        {/* Main forecast line */}
                        <Area
                            type="monotone"
                            dataKey="price"
                            name="Forecast"
                            stroke={lineColor}
                            strokeWidth={2}
                            fill="url(#forecastGradient)"
                            dot={false}
                            activeDot={{
                                r: 5,
                                stroke: lineColor,
                                strokeWidth: 2,
                                fill: '#0B0F19',
                            }}
                        />

                        {/* Reference line for current price */}
                        <ReferenceLine
                            y={currentPrice}
                            stroke="#64748b"
                            strokeDasharray="4 4"
                            strokeWidth={1}
                        />
                    </AreaChart>
                </ResponsiveContainer>
            </div>

            {/* Key Milestones Row */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(100px, 1fr))',
                gap: '0.5rem',
                marginTop: '1rem',
                paddingTop: '1rem',
                borderTop: '1px solid #1e293b',
            }}>
                {[0, 4, 9, 14, 19, 29].map((idx) => {
                    const item = forecast?.[idx]
                    if (!item) return null
                    const change = ((item.price - currentPrice) / currentPrice) * 100
                    const isUp = change >= 0

                    return (
                        <div key={idx} style={{
                            textAlign: 'center',
                            padding: '0.75rem 0.5rem',
                            borderRadius: '0.5rem',
                            background: '#0B0F19',
                            border: '1px solid #1e293b',
                        }}>
                            <p style={{ fontSize: '0.625rem', color: '#64748b', fontWeight: 500 }}>
                                Day {item.day}
                            </p>
                            <p style={{ fontSize: '0.875rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: '#f1f5f9' }}>
                                {currencySymbol}{item.price.toFixed(2)}
                            </p>
                            <p style={{
                                fontSize: '0.7rem',
                                fontWeight: 600,
                                fontFamily: 'var(--font-mono)',
                                color: isUp ? '#34d399' : '#fb7185',
                                marginTop: '0.125rem',
                            }}>
                                {isUp ? '+' : ''}{change.toFixed(1)}%
                            </p>
                        </div>
                    )
                })}
            </div>

            {/* Disclaimer */}
            <p style={{
                fontSize: '0.65rem',
                color: '#475569',
                textAlign: 'center',
                marginTop: '1rem',
                fontStyle: 'italic',
            }}>
                ⚠️ Forecast is generated using Monte Carlo simulations with technical indicators. This is not financial advice. Past performance does not guarantee future results.
            </p>
        </div>
    )
}
