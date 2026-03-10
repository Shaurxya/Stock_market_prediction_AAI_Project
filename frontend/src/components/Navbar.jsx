import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { TrendingUp, Menu, X, BarChart3, Home, Info } from 'lucide-react'

export default function Navbar() {
    const [isOpen, setIsOpen] = useState(false)
    const location = useLocation()

    const navLinks = [
        { to: '/', label: 'Home', icon: Home },
        { to: '/predict', label: 'Predictions', icon: BarChart3 },
        { to: '/about', label: 'About', icon: Info },
    ]

    const isActive = (path) => location.pathname === path

    return (
        <nav style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            zIndex: 50,
            background: 'rgba(11, 15, 25, 0.85)',
            backdropFilter: 'blur(16px)',
            WebkitBackdropFilter: 'blur(16px)',
            borderBottom: '1px solid #1e293b',
        }}>
            <div className="section-wrapper">
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: '64px' }}>

                    {/* Logo */}
                    <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', textDecoration: 'none' }}>
                        <div style={{
                            width: '2rem',
                            height: '2rem',
                            borderRadius: '0.5rem',
                            background: '#4f46e5',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                        }}>
                            <TrendingUp size={16} color="white" />
                        </div>
                        <span style={{ fontSize: '1.125rem', fontWeight: 600, color: '#f1f5f9', letterSpacing: '-0.025em' }}>StockAI</span>
                    </Link>

                    {/* Desktop Nav */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }} className="hidden-mobile">
                        {navLinks.map(({ to, label, icon: Icon }) => (
                            <Link
                                key={to}
                                to={to}
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.5rem',
                                    padding: '0.5rem 0.75rem',
                                    borderRadius: '0.5rem',
                                    fontSize: '0.875rem',
                                    fontWeight: 500,
                                    color: isActive(to) ? '#f1f5f9' : '#94a3b8',
                                    background: isActive(to) ? '#111827' : 'transparent',
                                    textDecoration: 'none',
                                    transition: 'color 0.2s, background 0.2s',
                                }}
                                onMouseEnter={e => {
                                    if (!isActive(to)) {
                                        e.currentTarget.style.color = '#f1f5f9'
                                        e.currentTarget.style.background = 'rgba(17,24,39,0.5)'
                                    }
                                }}
                                onMouseLeave={e => {
                                    if (!isActive(to)) {
                                        e.currentTarget.style.color = '#94a3b8'
                                        e.currentTarget.style.background = 'transparent'
                                    }
                                }}
                            >
                                <Icon size={16} style={{ color: isActive(to) ? '#818cf8' : undefined }} />
                                {label}
                            </Link>
                        ))}
                    </div>

                    {/* Mobile Menu Button */}
                    <button
                        className="show-mobile"
                        style={{
                            padding: '0.5rem',
                            borderRadius: '0.5rem',
                            color: '#94a3b8',
                            background: 'transparent',
                            border: 'none',
                            cursor: 'pointer',
                            display: 'none',
                        }}
                        onClick={() => setIsOpen(!isOpen)}
                        aria-label="Toggle menu"
                    >
                        {isOpen ? <X size={20} /> : <Menu size={20} />}
                    </button>
                </div>
            </div>

            {/* Mobile Menu */}
            {isOpen && (
                <div style={{
                    padding: '0.5rem 1.5rem 1rem',
                    background: '#0B0F19',
                    borderTop: '1px solid #1e293b',
                }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                        {navLinks.map(({ to, label, icon: Icon }) => (
                            <Link
                                key={to}
                                to={to}
                                onClick={() => setIsOpen(false)}
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.75rem',
                                    padding: '0.75rem',
                                    borderRadius: '0.5rem',
                                    fontSize: '0.875rem',
                                    fontWeight: 500,
                                    color: isActive(to) ? '#f1f5f9' : '#94a3b8',
                                    background: isActive(to) ? '#111827' : 'transparent',
                                    textDecoration: 'none',
                                }}
                            >
                                <Icon size={18} style={{ color: isActive(to) ? '#818cf8' : undefined }} />
                                {label}
                            </Link>
                        ))}
                    </div>
                </div>
            )}

            <style>{`
                @media (min-width: 769px) {
                    .hidden-mobile { display: flex !important; }
                    .show-mobile { display: none !important; }
                }
                @media (max-width: 768px) {
                    .hidden-mobile { display: none !important; }
                    .show-mobile { display: flex !important; }
                }
            `}</style>
        </nav>
    )
}
