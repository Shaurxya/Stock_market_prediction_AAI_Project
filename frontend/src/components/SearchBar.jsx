import { useState, useRef, useEffect } from 'react'
import { Search, ArrowRight, Loader2, ChevronDown, Globe } from 'lucide-react'

const MARKETS = [
    { id: 'auto', label: 'Auto', flag: '🌐', description: 'Auto-detect market' },
    { id: 'US', label: 'US', flag: '🇺🇸', description: 'NYSE / NASDAQ' },
    { id: 'NSE', label: 'NSE', flag: '🇮🇳', description: 'National Stock Exchange' },
    { id: 'BSE', label: 'BSE', flag: '🇮🇳', description: 'Bombay Stock Exchange' },
]

const QUICK_PICKS = {
    auto: [
        { ticker: 'AAPL', label: 'AAPL', market: 'US' },
        { ticker: 'NVDA', label: 'NVDA', market: 'US' },
        { ticker: 'TSLA', label: 'TSLA', market: 'US' },
        { ticker: 'RELIANCE', label: 'RELIANCE', market: 'NSE' },
        { ticker: 'TCS', label: 'TCS', market: 'NSE' },
        { ticker: 'INFY', label: 'INFY', market: 'NSE' },
    ],
    US: [
        { ticker: 'AAPL', label: 'AAPL' },
        { ticker: 'GOOGL', label: 'GOOGL' },
        { ticker: 'MSFT', label: 'MSFT' },
        { ticker: 'TSLA', label: 'TSLA' },
        { ticker: 'NVDA', label: 'NVDA' },
        { ticker: 'AMZN', label: 'AMZN' },
    ],
    NSE: [
        { ticker: 'RELIANCE', label: 'RELIANCE' },
        { ticker: 'TCS', label: 'TCS' },
        { ticker: 'INFY', label: 'INFY' },
        { ticker: 'HDFCBANK', label: 'HDFC' },
        { ticker: 'ICICIBANK', label: 'ICICI' },
        { ticker: 'SBIN', label: 'SBI' },
    ],
    BSE: [
        { ticker: 'RELIANCE', label: 'RELIANCE' },
        { ticker: 'TCS', label: 'TCS' },
        { ticker: 'INFY', label: 'INFY' },
        { ticker: 'HDFCBANK', label: 'HDFC' },
        { ticker: 'TATAMOTORS', label: 'TATA' },
        { ticker: 'WIPRO', label: 'WIPRO' },
    ],
}

export default function SearchBar({ onSearch, isLoading }) {
    const [ticker, setTicker] = useState('')
    const [market, setMarket] = useState('auto')
    const [dropdownOpen, setDropdownOpen] = useState(false)
    const dropdownRef = useRef(null)

    // Close dropdown on outside click
    useEffect(() => {
        const handleClick = (e) => {
            if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
                setDropdownOpen(false)
            }
        }
        document.addEventListener('mousedown', handleClick)
        return () => document.removeEventListener('mousedown', handleClick)
    }, [])

    const handleSubmit = (e) => {
        e.preventDefault()
        const value = ticker.trim().toUpperCase()
        if (value && !isLoading) {
            onSearch(value, market)
        }
    }

    const handleQuickPick = (t, m) => {
        const pickMarket = m || market
        setTicker(t)
        onSearch(t, pickMarket)
    }

    const selectedMarket = MARKETS.find((m) => m.id === market)
    const picks = QUICK_PICKS[market] || QUICK_PICKS.auto

    const placeholderText = market === 'NSE' || market === 'BSE'
        ? 'Enter ticker (e.g., RELIANCE, TCS, INFY)'
        : market === 'US'
            ? 'Enter ticker (e.g., AAPL, NVDA, TSLA)'
            : 'Enter ticker (e.g., AAPL, RELIANCE)'

    return (
        <div style={{ width: '100%' }}>
            {/* Search Form */}
            <form onSubmit={handleSubmit}>
                <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>

                    {/* Market Selector Button */}
                    <div ref={dropdownRef} style={{ position: 'absolute', left: '6px', zIndex: 10 }}>
                        <button
                            type="button"
                            onClick={() => setDropdownOpen(!dropdownOpen)}
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.25rem',
                                padding: '0.35rem 0.5rem',
                                borderRadius: '6px',
                                fontSize: '0.75rem',
                                fontWeight: 600,
                                background: 'rgba(99, 102, 241, 0.12)',
                                color: '#818cf8',
                                border: '1px solid rgba(99, 102, 241, 0.2)',
                                cursor: 'pointer',
                                transition: 'all 0.2s',
                                fontFamily: 'var(--font-mono)',
                                letterSpacing: '0.02em',
                            }}
                            onMouseEnter={(e) => {
                                e.currentTarget.style.background = 'rgba(99, 102, 241, 0.2)'
                                e.currentTarget.style.borderColor = 'rgba(99, 102, 241, 0.4)'
                            }}
                            onMouseLeave={(e) => {
                                e.currentTarget.style.background = 'rgba(99, 102, 241, 0.12)'
                                e.currentTarget.style.borderColor = 'rgba(99, 102, 241, 0.2)'
                            }}
                        >
                            <span>{selectedMarket.flag}</span>
                            <span>{selectedMarket.label}</span>
                            <ChevronDown size={12} style={{
                                transform: dropdownOpen ? 'rotate(180deg)' : 'rotate(0deg)',
                                transition: 'transform 0.2s',
                            }} />
                        </button>

                        {/* Dropdown */}
                        {dropdownOpen && (
                            <div style={{
                                position: 'absolute',
                                top: 'calc(100% + 6px)',
                                left: 0,
                                background: '#111827',
                                border: '1px solid #1e293b',
                                borderRadius: '10px',
                                padding: '0.375rem',
                                minWidth: '200px',
                                boxShadow: '0 12px 40px rgba(0,0,0,0.5)',
                                zIndex: 50,
                            }}>
                                {MARKETS.map((m) => (
                                    <button
                                        key={m.id}
                                        type="button"
                                        onClick={() => {
                                            setMarket(m.id)
                                            setDropdownOpen(false)
                                        }}
                                        style={{
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '0.625rem',
                                            width: '100%',
                                            padding: '0.5rem 0.625rem',
                                            borderRadius: '6px',
                                            fontSize: '0.8rem',
                                            color: market === m.id ? '#818cf8' : '#94a3b8',
                                            background: market === m.id ? 'rgba(99, 102, 241, 0.1)' : 'transparent',
                                            border: 'none',
                                            cursor: 'pointer',
                                            textAlign: 'left',
                                            transition: 'background 0.15s',
                                        }}
                                        onMouseEnter={(e) => {
                                            if (market !== m.id) e.currentTarget.style.background = '#1e293b'
                                        }}
                                        onMouseLeave={(e) => {
                                            if (market !== m.id) e.currentTarget.style.background = 'transparent'
                                        }}
                                    >
                                        <span style={{ fontSize: '1rem' }}>{m.flag}</span>
                                        <div>
                                            <div style={{ fontWeight: 600, fontFamily: 'var(--font-mono)' }}>{m.label}</div>
                                            <div style={{ fontSize: '0.65rem', color: '#64748b', marginTop: '1px' }}>{m.description}</div>
                                        </div>
                                        {market === m.id && (
                                            <span style={{ marginLeft: 'auto', color: '#818cf8', fontSize: '0.75rem' }}>✓</span>
                                        )}
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Search Icon */}
                    <Search size={16} style={{ position: 'absolute', left: '5.75rem', color: '#475569' }} />

                    {/* Input */}
                    <input
                        id="search-ticker"
                        type="text"
                        value={ticker}
                        onChange={(e) => setTicker(e.target.value.toUpperCase())}
                        placeholder={placeholderText}
                        className="input-field"
                        style={{
                            paddingLeft: '7.5rem',
                            paddingRight: '7rem',
                            height: '52px',
                            fontFamily: 'var(--font-mono)',
                            fontSize: '0.95rem',
                            letterSpacing: '0.03em',
                        }}
                        maxLength={20}
                        disabled={isLoading}
                    />

                    {/* Predict Button */}
                    <button
                        type="submit"
                        disabled={!ticker.trim() || isLoading}
                        className="btn-primary"
                        style={{
                            position: 'absolute',
                            right: '6px',
                            padding: '0.5rem 1rem',
                            borderRadius: '6px',
                            fontSize: '0.85rem',
                        }}
                    >
                        {isLoading ? (
                            <Loader2 size={16} className="animate-spin" />
                        ) : (
                            <>
                                Predict
                                <ArrowRight size={14} />
                            </>
                        )}
                    </button>
                </div>
            </form>

            {/* Quick Picks */}
            <div style={{
                display: 'flex',
                flexWrap: 'wrap',
                alignItems: 'center',
                gap: '0.5rem',
                marginTop: '0.75rem',
                justifyContent: 'center',
            }}>
                <span style={{ fontSize: '0.7rem', color: '#475569', fontWeight: 500 }}>Quick:</span>
                {picks.map((p, i) => (
                    <button
                        key={`${p.ticker}-${i}`}
                        onClick={() => handleQuickPick(p.ticker, p.market)}
                        disabled={isLoading}
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.3rem',
                            padding: '0.25rem 0.625rem',
                            borderRadius: '0.375rem',
                            fontSize: '0.7rem',
                            fontWeight: 500,
                            background: '#111827',
                            color: '#94a3b8',
                            border: '1px solid #1e293b',
                            cursor: isLoading ? 'not-allowed' : 'pointer',
                            fontFamily: 'var(--font-mono)',
                            transition: 'border-color 0.2s, background 0.2s',
                        }}
                        onMouseEnter={(e) => {
                            e.target.style.background = '#1e293b'
                            e.target.style.borderColor = '#334155'
                        }}
                        onMouseLeave={(e) => {
                            e.target.style.background = '#111827'
                            e.target.style.borderColor = '#1e293b'
                        }}
                    >
                        {p.market && (
                            <span style={{
                                fontSize: '0.6rem',
                                color: p.market === 'NSE' || p.market === 'BSE' ? '#f59e0b' : '#6366f1',
                                fontWeight: 700,
                            }}>
                                {p.market === 'NSE' ? '🇮🇳' : p.market === 'BSE' ? '🇮🇳' : '🇺🇸'}
                            </span>
                        )}
                        {p.label}
                    </button>
                ))}
            </div>
        </div>
    )
}
