import { useNavigate } from 'react-router-dom'
import { TrendingUp, Brain, Cpu, Layers, BarChart3, ArrowRight, Search, Activity, Target, Zap } from 'lucide-react'

const features = [
    {
        icon: Brain,
        title: 'LSTM Neural Network',
        desc: 'Deep learning model trained on sequential time-series data with 60-day lookback windows for long-term pattern recognition.',
    },
    {
        icon: Cpu,
        title: 'XGBoost Classifier',
        desc: 'Gradient boosted ensemble model for high-accuracy trend classification with structural feature importance analysis.',
    },
    {
        icon: Layers,
        title: 'Ensemble Analysis',
        desc: 'Combined predictions from both models to deliver higher reliability, reduced variance, and calibrated confidence scoring.',
    },
    {
        icon: BarChart3,
        title: 'Technical Indicators',
        desc: 'Processing of SMA, EMA, RSI, MACD, Bollinger Bands, and lag features to capture market momentum.',
    },
]

const steps = [
    {
        icon: Search,
        title: 'Select Asset',
        desc: 'Enter any market ticker to pull standardized historical pricing data.',
        step: '01',
    },
    {
        icon: Activity,
        title: 'Data Processing',
        desc: 'Our pipeline computes technical indicators, lag features, and oscillators.',
        step: '02',
    },
    {
        icon: Zap,
        title: 'Run Inference',
        desc: 'Models execute forward pass and converge on a predicted directional trend.',
        step: '03',
    },
    {
        icon: Target,
        title: 'Review Output',
        desc: 'Analyze predictions alongside granular confidence levels and price forecasts.',
        step: '04',
    },
]

const stats = [
    { label: 'Technical Indicators', value: '15+' },
    { label: 'Models Deployed', value: '2' },
    { label: 'Lag Features', value: '5' },
    { label: 'Lookback Window', value: '60d' },
]

function HeroSection() {
    const navigate = useNavigate()

    return (
        <section style={{ paddingTop: '6rem', paddingBottom: '6rem' }}>
            <div className="section-wrapper" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', gap: '2rem' }}>
                {/* Badge */}
                <div style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    padding: '0.375rem 0.875rem',
                    borderRadius: '9999px',
                    background: '#111827',
                    border: '1px solid #1e293b',
                    fontSize: '0.75rem',
                    fontWeight: 500,
                    color: '#94a3b8',
                }}>
                    <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#4f46e5' }} />
                    AI-Powered Stock Predictions
                </div>

                {/* Heading */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', maxWidth: '48rem' }}>
                    <h1 style={{
                        fontSize: 'clamp(2.25rem, 5vw, 3.5rem)',
                        fontWeight: 600,
                        letterSpacing: '-0.025em',
                        lineHeight: 1.1,
                        color: '#f1f5f9',
                    }}>
                        Institutional-grade<br />
                        stock trend analysis.
                    </h1>

                    <p style={{
                        fontSize: '1.125rem',
                        color: '#94a3b8',
                        lineHeight: 1.7,
                        maxWidth: '40rem',
                        marginLeft: 'auto',
                        marginRight: 'auto',
                    }}>
                        Harness the power of LSTM neural networks and XGBoost algorithms to forecast stock price movements with real-time analysis and confidence scoring.
                    </p>
                </div>

                {/* CTAs */}
                <div style={{ display: 'flex', gap: '0.75rem', paddingTop: '0.5rem', flexWrap: 'wrap', justifyContent: 'center' }}>
                    <button
                        onClick={() => navigate('/predict')}
                        style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                            padding: '0.75rem 1.5rem',
                            borderRadius: '0.5rem',
                            background: '#4f46e5',
                            color: 'white',
                            fontSize: '0.875rem',
                            fontWeight: 500,
                            border: 'none',
                            cursor: 'pointer',
                            transition: 'background 0.2s',
                        }}
                        onMouseEnter={e => e.currentTarget.style.background = '#6366f1'}
                        onMouseLeave={e => e.currentTarget.style.background = '#4f46e5'}
                    >
                        Start Analysis
                        <ArrowRight size={16} />
                    </button>
                    <button
                        onClick={() => document.getElementById('architecture')?.scrollIntoView({ behavior: 'smooth' })}
                        style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                            padding: '0.75rem 1.5rem',
                            borderRadius: '0.5rem',
                            background: 'transparent',
                            color: '#cbd5e1',
                            fontSize: '0.875rem',
                            fontWeight: 500,
                            border: '1px solid #1e293b',
                            cursor: 'pointer',
                            transition: 'border-color 0.2s',
                        }}
                        onMouseEnter={e => e.currentTarget.style.borderColor = '#334155'}
                        onMouseLeave={e => e.currentTarget.style.borderColor = '#1e293b'}
                    >
                        View Architecture
                    </button>
                </div>
            </div>
        </section>
    )
}

function StatsSection() {
    return (
        <section style={{ paddingTop: '4rem', paddingBottom: '4rem', borderTop: '1px solid #1e293b', borderBottom: '1px solid #1e293b', background: 'rgba(17,24,39,0.3)' }}>
            <div className="section-wrapper">
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(4, 1fr)',
                    gap: '2rem',
                    textAlign: 'center',
                }}>
                    {stats.map(({ label, value }) => (
                        <div key={label} style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                            <p style={{
                                fontSize: '2rem',
                                fontWeight: 600,
                                color: '#f1f5f9',
                                letterSpacing: '-0.025em',
                                fontFamily: 'var(--font-mono)',
                            }}>
                                {value}
                            </p>
                            <p style={{ fontSize: '0.875rem', color: '#64748b', fontWeight: 500 }}>{label}</p>
                        </div>
                    ))}
                </div>
            </div>
        </section>
    )
}

function FeaturesSection() {
    return (
        <section id="architecture" style={{ paddingTop: '6rem', paddingBottom: '6rem' }}>
            <div className="section-wrapper" style={{ display: 'flex', flexDirection: 'column', gap: '4rem' }}>
                {/* Section header */}
                <div style={{ maxWidth: '36rem' }}>
                    <h2 style={{
                        fontSize: '1.875rem',
                        fontWeight: 600,
                        letterSpacing: '-0.025em',
                        color: '#f1f5f9',
                        marginBottom: '1rem',
                    }}>
                        Built for professional analysis
                    </h2>
                    <p style={{ fontSize: '1.125rem', color: '#94a3b8', lineHeight: 1.7 }}>
                        Our dual-model architecture processes complex time-series data and technical indicators to produce high-confidence trend classifications.
                    </p>
                </div>

                {/* Feature grid */}
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(2, 1fr)',
                    gap: '1.5rem',
                }}>
                    {features.map(({ icon: Icon, title, desc }) => (
                        <div key={title} style={{
                            background: '#111827',
                            border: '1px solid #1e293b',
                            borderRadius: '0.75rem',
                            padding: '2rem',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '1rem',
                            transition: 'border-color 0.2s',
                        }}
                            onMouseEnter={e => e.currentTarget.style.borderColor = '#334155'}
                            onMouseLeave={e => e.currentTarget.style.borderColor = '#1e293b'}
                        >
                            <div style={{
                                width: '2.5rem',
                                height: '2.5rem',
                                borderRadius: '0.5rem',
                                background: 'rgba(30,41,59,0.5)',
                                border: '1px solid rgba(51,65,85,0.5)',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                            }}>
                                <Icon size={20} style={{ color: '#94a3b8' }} />
                            </div>
                            <div>
                                <h3 style={{ fontSize: '1.125rem', fontWeight: 600, color: '#f1f5f9', marginBottom: '0.5rem' }}>
                                    {title}
                                </h3>
                                <p style={{ fontSize: '0.875rem', color: '#94a3b8', lineHeight: 1.7 }}>
                                    {desc}
                                </p>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </section>
    )
}

function HowItWorks() {
    return (
        <section style={{ paddingTop: '6rem', paddingBottom: '6rem', background: 'rgba(17,24,39,0.3)', borderTop: '1px solid #1e293b', borderBottom: '1px solid #1e293b' }}>
            <div className="section-wrapper" style={{ display: 'flex', flexDirection: 'column', gap: '4rem' }}>
                {/* Section header */}
                <div style={{ textAlign: 'center', maxWidth: '32rem', marginLeft: 'auto', marginRight: 'auto' }}>
                    <h2 style={{
                        fontSize: '1.875rem',
                        fontWeight: 600,
                        letterSpacing: '-0.025em',
                        color: '#f1f5f9',
                        marginBottom: '1rem',
                    }}>
                        Prediction Pipeline
                    </h2>
                    <p style={{ fontSize: '1.125rem', color: '#94a3b8', lineHeight: 1.7 }}>
                        A deterministic system for deriving market insights.
                    </p>
                </div>

                {/* Steps grid */}
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(4, 1fr)',
                    gap: '1.5rem',
                }}>
                    {steps.map(({ icon: Icon, title, desc, step }) => (
                        <div key={title} style={{
                            background: '#0B0F19',
                            border: '1px solid #1e293b',
                            borderRadius: '0.75rem',
                            padding: '1.5rem',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '1rem',
                            transition: 'border-color 0.2s',
                        }}
                            onMouseEnter={e => e.currentTarget.style.borderColor = '#334155'}
                            onMouseLeave={e => e.currentTarget.style.borderColor = '#1e293b'}
                        >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                <div style={{
                                    padding: '0.625rem',
                                    borderRadius: '0.5rem',
                                    background: 'rgba(79,70,229,0.1)',
                                    color: '#818cf8',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                }}>
                                    <Icon size={18} />
                                </div>
                                <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', fontWeight: 500, color: '#475569' }}>{step}</span>
                            </div>
                            <div>
                                <h3 style={{ fontSize: '1rem', fontWeight: 600, color: '#f1f5f9', marginBottom: '0.5rem' }}>
                                    {title}
                                </h3>
                                <p style={{ fontSize: '0.875rem', color: '#94a3b8', lineHeight: 1.7 }}>
                                    {desc}
                                </p>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </section>
    )
}

function CTASection() {
    const navigate = useNavigate()

    return (
        <section style={{ paddingTop: '6rem', paddingBottom: '6rem' }}>
            <div className="section-wrapper">
                <div style={{
                    background: '#111827',
                    border: '1px solid #1e293b',
                    borderRadius: '1rem',
                    padding: '4rem 3rem',
                    textAlign: 'center',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    gap: '2rem',
                }}>
                    <div style={{ maxWidth: '32rem' }}>
                        <h2 style={{
                            fontSize: '1.875rem',
                            fontWeight: 600,
                            letterSpacing: '-0.025em',
                            color: '#f1f5f9',
                            marginBottom: '1rem',
                        }}>
                            Ready to analyze the market?
                        </h2>
                        <p style={{ fontSize: '1.125rem', color: '#94a3b8', lineHeight: 1.7 }}>
                            Enter any stock ticker to get instant AI-powered predictions with confidence scores.
                        </p>
                    </div>
                    <button
                        onClick={() => navigate('/predict')}
                        style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                            padding: '0.875rem 2rem',
                            borderRadius: '0.5rem',
                            background: '#4f46e5',
                            color: 'white',
                            fontSize: '0.875rem',
                            fontWeight: 500,
                            border: 'none',
                            cursor: 'pointer',
                            transition: 'background 0.2s',
                        }}
                        onMouseEnter={e => e.currentTarget.style.background = '#6366f1'}
                        onMouseLeave={e => e.currentTarget.style.background = '#4f46e5'}
                    >
                        <TrendingUp size={16} />
                        Get Started
                    </button>
                </div>
            </div>
        </section>
    )
}

export default function Home() {
    return (
        <div style={{ width: '100%' }}>
            <HeroSection />
            <StatsSection />
            <FeaturesSection />
            <HowItWorks />
            <CTASection />
        </div>
    )
}
