import { useState, useMemo } from 'react'
import {
    AreaChart, Area, XAxis, YAxis, CartesianGrid,
    Tooltip, ResponsiveContainer
} from 'recharts'

const PERIOD_OPTIONS = [
    { label: '1M', value: '1mo' },
    { label: '3M', value: '3mo' },
    { label: '6M', value: '6mo' },
    { label: '1Y', value: '1y' },
    { label: '2Y', value: '2y' },
]

function CustomTooltip({ active, payload, label, currencySymbol = '$' }) {
    if (!active || !payload?.length) return null

    return (
        <div style={{
            background: '#111827',
            border: '1px solid #1e293b',
            borderRadius: '8px',
            padding: '10px 14px',
            minWidth: '160px',
        }}>
            <p style={{ fontSize: '0.75rem', marginBottom: '0.375rem', color: '#64748b' }}>{label}</p>
            {payload.map((entry, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem' }}>
                    <span style={{ fontSize: '0.75rem', color: entry.color }}>{entry.name}</span>
                    <span style={{ fontSize: '0.875rem', fontWeight: 600, color: '#f1f5f9', fontFamily: 'var(--font-mono)' }}>
                        {currencySymbol}{Number(entry.value).toFixed(2)}
                    </span>
                </div>
            ))}
        </div>
    )
}

export default function StockChart({ data, ticker, onPeriodChange, activePeriod, currency }) {
    const currencySymbol = currency === 'INR' ? '₹' : '$'
    const chartData = useMemo(() => {
        if (!data?.length) return []
        return data.map(item => ({
            ...item,
            date: item.date,
            close: Number(item.close),
            open: Number(item.open),
            high: Number(item.high),
            low: Number(item.low),
            volume: Number(item.volume),
        }))
    }, [data])

    const priceChange = useMemo(() => {
        if (chartData.length < 2) return { value: 0, percent: 0, isUp: true }
        const first = chartData[0].close
        const last = chartData[chartData.length - 1].close
        const change = last - first
        const percent = (change / first) * 100
        return { value: change, percent, isUp: change >= 0 }
    }, [chartData])

    if (!chartData.length) return null

    const currentPrice = chartData[chartData.length - 1]?.close
    const lineColor = priceChange.isUp ? '#10b981' : '#f43f5e'

    return (
        <div className="card fade-in-up" style={{ padding: '1.5rem' }}>
            {/* Header */}
            <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '1rem', marginBottom: '1.5rem' }}>
                <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.25rem' }}>
                        <h2 style={{ fontSize: '1.125rem', fontWeight: 600, color: '#f1f5f9' }}>{ticker}</h2>
                        <span className={`trend-badge ${priceChange.isUp ? 'up' : 'down'}`}>
                            {priceChange.isUp ? '▲' : '▼'} {Math.abs(priceChange.percent).toFixed(2)}%
                        </span>
                    </div>
                    <p style={{ fontSize: '1.25rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: '#f1f5f9' }}>
                        {currencySymbol}{currentPrice?.toFixed(2)}
                        <span style={{ fontSize: '0.875rem', marginLeft: '0.5rem', color: priceChange.isUp ? '#34d399' : '#fb7185' }}>
                            {priceChange.isUp ? '+' : ''}{priceChange.value.toFixed(2)}
                        </span>
                    </p>
                </div>

                {/* Period Selector */}
                <div style={{
                    display: 'flex',
                    gap: '2px',
                    padding: '3px',
                    borderRadius: '0.5rem',
                    background: '#111827',
                    border: '1px solid #1e293b',
                }}>
                    {PERIOD_OPTIONS.map(({ label, value }) => (
                        <button key={value}
                            onClick={() => onPeriodChange?.(value)}
                            style={{
                                padding: '0.375rem 0.75rem',
                                borderRadius: '0.375rem',
                                fontSize: '0.75rem',
                                fontWeight: 500,
                                background: activePeriod === value ? '#1e293b' : 'transparent',
                                color: activePeriod === value ? '#f1f5f9' : '#64748b',
                                border: 'none',
                                cursor: 'pointer',
                                transition: 'all 0.2s',
                            }}
                        >
                            {label}
                        </button>
                    ))}
                </div>
            </div>

            {/* Chart */}
            <div style={{ width: '100%', height: 360 }}>
                <ResponsiveContainer>
                    <AreaChart data={chartData} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
                        <defs>
                            <linearGradient id="colorClose" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stopColor={lineColor} stopOpacity={0.15} />
                                <stop offset="95%" stopColor={lineColor} stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                        <XAxis
                            dataKey="date"
                            tick={{ fontSize: 11, fill: '#64748b' }}
                            tickLine={false}
                            axisLine={{ stroke: '#1e293b' }}
                            interval="preserveStartEnd"
                            tickFormatter={(val) => {
                                const d = new Date(val)
                                return `${d.getMonth() + 1}/${d.getDate()}`
                            }}
                        />
                        <YAxis
                            tick={{ fontSize: 11, fill: '#64748b' }}
                            tickLine={false}
                            axisLine={false}
                            domain={['auto', 'auto']}
                            tickFormatter={(val) => `${currencySymbol}${val}`}
                            width={65}
                        />
                        <Tooltip content={<CustomTooltip currencySymbol={currencySymbol} />} />
                        <Area
                            type="monotone"
                            dataKey="close"
                            name="Close"
                            stroke={lineColor}
                            strokeWidth={1.5}
                            fill="url(#colorClose)"
                            dot={false}
                            activeDot={{ r: 4, stroke: lineColor, strokeWidth: 2, fill: '#0B0F19' }}
                        />
                    </AreaChart>
                </ResponsiveContainer>
            </div>
        </div>
    )
}
