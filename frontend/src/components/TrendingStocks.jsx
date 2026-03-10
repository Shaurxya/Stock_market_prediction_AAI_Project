import { Zap, ArrowRight } from 'lucide-react'

const MARKET_COLORS = {
    US: { bg: 'rgba(99, 102, 241, 0.1)', color: '#818cf8', border: 'rgba(99, 102, 241, 0.15)' },
    NSE: { bg: 'rgba(245, 158, 11, 0.1)', color: '#f59e0b', border: 'rgba(245, 158, 11, 0.15)' },
    BSE: { bg: 'rgba(245, 158, 11, 0.1)', color: '#f59e0b', border: 'rgba(245, 158, 11, 0.15)' },
}

export default function TrendingStocks({ stocks, onSelect, isLoading }) {
    if (!stocks?.length) return null

    // Separate US and Indian stocks
    const usStocks = stocks.filter((s) => s.market === 'US' || !s.market)
    const indiaStocks = stocks.filter((s) => s.market === 'NSE' || s.market === 'BSE')

    const renderSection = (title, emoji, stockList) => {
        if (!stockList.length) return null
        return (
            <div style={{ marginBottom: '1rem' }}>
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.375rem',
                    marginBottom: '0.625rem',
                }}>
                    <span style={{ fontSize: '0.75rem' }}>{emoji}</span>
                    <span style={{
                        fontSize: '0.7rem',
                        fontWeight: 600,
                        color: '#64748b',
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em',
                        fontFamily: 'var(--font-mono)',
                    }}>
                        {title}
                    </span>
                </div>
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(4, 1fr)',
                    gap: '0.5rem',
                }}>
                    {stockList.map((stock) => {
                        const mColors = MARKET_COLORS[stock.market] || MARKET_COLORS.US
                        return (
                            <button
                                key={stock.ticker}
                                onClick={() => onSelect(stock.ticker)}
                                disabled={isLoading}
                                style={{
                                    display: 'flex',
                                    flexDirection: 'column',
                                    alignItems: 'flex-start',
                                    padding: '0.75rem',
                                    borderRadius: '0.5rem',
                                    background: '#0B0F19',
                                    border: '1px solid #1e293b',
                                    cursor: isLoading ? 'not-allowed' : 'pointer',
                                    textAlign: 'left',
                                    transition: 'border-color 0.2s',
                                }}
                                onMouseEnter={(e) => {
                                    e.currentTarget.style.borderColor = '#334155'
                                }}
                                onMouseLeave={(e) => {
                                    e.currentTarget.style.borderColor = '#1e293b'
                                }}
                            >
                                <div style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'space-between',
                                    width: '100%',
                                    marginBottom: '0.25rem',
                                }}>
                                    <span style={{
                                        fontSize: '0.8rem',
                                        fontWeight: 600,
                                        color: '#f1f5f9',
                                        fontFamily: 'var(--font-mono)',
                                    }}>
                                        {stock.ticker.replace('.NS', '').replace('.BO', '')}
                                    </span>
                                    <span style={{
                                        fontSize: '0.55rem',
                                        fontWeight: 700,
                                        padding: '0.1rem 0.3rem',
                                        borderRadius: '3px',
                                        background: mColors.bg,
                                        color: mColors.color,
                                        border: `1px solid ${mColors.border}`,
                                        fontFamily: 'var(--font-mono)',
                                    }}>
                                        {stock.market || 'US'}
                                    </span>
                                </div>
                                <span style={{
                                    fontSize: '0.6rem',
                                    color: '#64748b',
                                    lineHeight: 1.3,
                                    overflow: 'hidden',
                                    textOverflow: 'ellipsis',
                                    whiteSpace: 'nowrap',
                                    width: '100%',
                                }}>
                                    {stock.name}
                                </span>
                            </button>
                        )
                    })}
                </div>
            </div>
        )
    }

    return (
        <div className="card fade-in-up fade-in-up-delay-2" style={{ padding: '1.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.125rem' }}>
                <Zap size={16} style={{ color: '#f59e0b' }} />
                <h3 style={{ fontSize: '0.875rem', fontWeight: 600, color: '#f1f5f9' }}>
                    Popular Stocks
                </h3>
            </div>

            {renderSection('US Market', '🇺🇸', usStocks)}
            {renderSection('Indian Market', '🇮🇳', indiaStocks)}

            <style>{`
                @media (max-width: 768px) {
                    .trending-grid { grid-template-columns: repeat(2, 1fr) !important; }
                }
            `}</style>
        </div>
    )
}
