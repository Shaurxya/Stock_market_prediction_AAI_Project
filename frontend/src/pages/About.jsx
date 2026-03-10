import {
    Brain, Cpu, Database, Server, MonitorSmartphone, GitBranch,
    BookOpen, Layers, Target, TrendingUp, BarChart3, Zap,
    Shield, Globe, LineChart, Clock, Users, Lightbulb,
    ChevronRight, Activity, PieChart, Calendar, Sparkles
} from 'lucide-react'

/* ─── Slide Data ──────────────────────────────────────────────────────── */

const pipelineSteps = [
    {
        step: '01',
        title: 'Data Ingestion',
        desc: 'Historical OHLCV stock data is fetched in real-time from Yahoo Finance using the yfinance API. Supports US stocks, Indian NSE (.NS), and Indian BSE (.BO) markets.',
        icon: Database,
        color: '#3b82f6',
    },
    {
        step: '02',
        title: 'Feature Engineering',
        desc: '29 technical indicators are computed — SMA, EMA, RSI, MACD, Bollinger Bands, lag features, rolling volatility, volume ratios, and price ranges — creating a rich feature matrix.',
        icon: Activity,
        color: '#8b5cf6',
    },
    {
        step: '03',
        title: 'Ensemble AI Prediction',
        desc: 'LSTM deep learning processes 60-day sequences for temporal patterns. XGBoost classifies the latest feature vector. Probabilities are averaged into an ensemble prediction.',
        icon: Brain,
        color: '#ec4899',
    },
    {
        step: '04',
        title: '30-Day Monte Carlo Forecast',
        desc: '100 Monte Carlo simulations are run using drift, RSI mean-reversion, MACD momentum, SMA crossover trends, and historical volatility to generate a 30-day price forecast with confidence bands.',
        icon: LineChart,
        color: '#f59e0b',
    },
    {
        step: '05',
        title: 'Visualization & Results',
        desc: 'Predictions, forecasts, and historical data are rendered as interactive charts with confidence scores, probability breakdowns, and currency-aware pricing (₹ / $).',
        icon: BarChart3,
        color: '#10b981',
    },
]

const techStack = [
    { icon: Brain, name: 'TensorFlow / Keras', desc: 'LSTM deep learning model with Bidirectional layers', category: 'AI/ML' },
    { icon: Cpu, name: 'XGBoost', desc: 'Gradient boosted decision tree classifier', category: 'AI/ML' },
    { icon: Server, name: 'FastAPI', desc: 'High-performance Python REST API backend', category: 'Backend' },
    { icon: MonitorSmartphone, name: 'React + Vite', desc: 'Modern SPA frontend with hot-reload', category: 'Frontend' },
    { icon: Database, name: 'yfinance', desc: 'Real-time stock data from Yahoo Finance', category: 'Data' },
    { icon: LineChart, name: 'Recharts', desc: 'Composable charting library for React', category: 'Frontend' },
    { icon: GitBranch, name: 'scikit-learn', desc: 'Preprocessing, scaling, and evaluation metrics', category: 'AI/ML' },
    { icon: Layers, name: 'Pandas + NumPy', desc: 'Data manipulation and numerical computing', category: 'Data' },
]

const features = [
    { name: 'SMA (20, 50)', type: 'Trend', desc: 'Simple Moving Averages for short & medium-term trend' },
    { name: 'EMA (12, 26)', type: 'Trend', desc: 'Exponential Moving Averages for responsive trend tracking' },
    { name: 'RSI (14)', type: 'Momentum', desc: 'Relative Strength Index — overbought / oversold signals' },
    { name: 'MACD + Signal + Histogram', type: 'Momentum', desc: 'Moving Average Convergence Divergence & crossovers' },
    { name: 'Bollinger Bands', type: 'Volatility', desc: 'Upper, Lower bands, Width, and Price Position' },
    { name: 'Lag Features (1–5)', type: 'Temporal', desc: 'Past 5 days closing prices as input features' },
    { name: 'Daily & Log Returns', type: 'Returns', desc: 'Percentage and logarithmic daily price changes' },
    { name: 'Rolling Volatility (20d)', type: 'Volatility', desc: '20-day rolling standard deviation of returns' },
    { name: 'Volume Ratio', type: 'Volume', desc: 'Current volume vs 20-day average volume' },
    { name: 'Price Ranges', type: 'Price', desc: 'High-Low and Open-Close ranges normalized by price' },
]

const objectives = [
    { icon: TrendingUp, text: 'Predict next-day stock trend direction (Up/Down) using AI models' },
    { icon: Calendar, text: 'Generate 30-day price forecasts using Monte Carlo simulations' },
    { icon: Globe, text: 'Support multi-market stocks — US, Indian NSE, and Indian BSE' },
    { icon: Layers, text: 'Combine LSTM and XGBoost into an ensemble prediction system' },
    { icon: BarChart3, text: 'Visualize predictions with interactive charts and confidence scores' },
    { icon: Shield, text: 'Build a production-ready API with robust error handling' },
]

const keyResults = [
    { label: 'Technical Indicators', value: '29', suffix: 'features' },
    { label: 'LSTM Lookback', value: '60', suffix: 'days' },
    { label: 'Forecast Horizon', value: '30', suffix: 'days' },
    { label: 'MC Simulations', value: '100', suffix: 'paths' },
    { label: 'Markets Supported', value: '3', suffix: 'US · NSE · BSE' },
    { label: 'Models in Ensemble', value: '2', suffix: 'LSTM + XGBoost' },
]

const futureScope = [
    { icon: Sparkles, title: 'Sentiment Analysis', desc: 'Integrate news and social media sentiment as additional model features' },
    { icon: Users, title: 'User Portfolios', desc: 'Allow users to create watchlists and track predictions over time' },
    { icon: Zap, title: 'Real-Time Streaming', desc: 'WebSocket-based live price updates and intraday predictions' },
    { icon: PieChart, title: 'More Models', desc: 'Add Transformer, GRU, and Random Forest models for stronger ensembles' },
]

/* ─── Slide Number Badge ──────────────────────────────────────────────── */

function SlideBadge({ number }) {
    return (
        <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.5rem',
            background: 'rgba(129,140,248,0.1)',
            border: '1px solid rgba(129,140,248,0.2)',
            borderRadius: '2rem',
            padding: '0.25rem 0.875rem',
            marginBottom: '1rem',
        }}>
            <span style={{ fontSize: '0.65rem', fontWeight: 700, color: '#818cf8', fontFamily: 'var(--font-mono)' }}>
                SLIDE {String(number).padStart(2, '0')}
            </span>
        </div>
    )
}

/* ─── Section Heading inside Cards ───────────────────────────────────── */

function CardHeader({ icon: Icon, title, subtitle, color = '#818cf8' }) {
    return (
        <div style={{ marginBottom: '1.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
                <div style={{
                    width: '2.5rem',
                    height: '2.5rem',
                    borderRadius: '0.625rem',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background: `${color}15`,
                    border: `1px solid ${color}30`,
                }}>
                    <Icon size={18} style={{ color }} />
                </div>
                <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: '#f1f5f9' }}>{title}</h2>
            </div>
            {subtitle && (
                <p style={{ fontSize: '0.9rem', color: '#94a3b8', lineHeight: 1.7, marginLeft: '3.25rem' }}>
                    {subtitle}
                </p>
            )}
        </div>
    )
}

/* ─── Type Badge for Features ────────────────────────────────────────── */

const typeColors = {
    Trend: '#3b82f6',
    Momentum: '#f59e0b',
    Volatility: '#ef4444',
    Temporal: '#8b5cf6',
    Returns: '#10b981',
    Volume: '#06b6d4',
    Price: '#ec4899',
}

/* ─── Main About Page ────────────────────────────────────────────────── */

export default function About() {
    return (
        <section style={{ paddingTop: '6rem', paddingBottom: '6rem', width: '100%' }}>
            <div className="section-wrapper" style={{ display: 'flex', flexDirection: 'column', gap: '2.5rem' }}>

                {/* ═══════════ SLIDE 1 — Title ═══════════ */}
                <div className="card fade-in-up" style={{
                    padding: '3rem 2.5rem',
                    textAlign: 'center',
                    background: 'linear-gradient(135deg, rgba(129,140,248,0.08) 0%, rgba(15,23,42,0.9) 50%, rgba(16,185,129,0.06) 100%)',
                    border: '1px solid rgba(129,140,248,0.15)',
                    position: 'relative',
                    overflow: 'hidden',
                }}>
                    <div style={{
                        position: 'absolute',
                        top: '-50%',
                        left: '-20%',
                        width: '140%',
                        height: '200%',
                        background: 'radial-gradient(ellipse at center, rgba(129,140,248,0.04) 0%, transparent 70%)',
                        pointerEvents: 'none',
                    }} />
                    <SlideBadge number={1} />
                    <h1 style={{
                        fontSize: '2.5rem',
                        fontWeight: 700,
                        letterSpacing: '-0.03em',
                        marginBottom: '1rem',
                        background: 'linear-gradient(135deg, #818cf8, #34d399)',
                        WebkitBackgroundClip: 'text',
                        WebkitTextFillColor: 'transparent',
                    }}>
                        Stock Market Prediction System
                    </h1>
                    <p style={{ fontSize: '1.125rem', color: '#94a3b8', lineHeight: 1.8, maxWidth: '40rem', margin: '0 auto 1.5rem' }}>
                        An AI-powered stock market prediction system that combines <strong style={{ color: '#818cf8' }}>LSTM Deep Learning</strong> and <strong style={{ color: '#34d399' }}>XGBoost Ensemble</strong> methods to predict trends, generate 30-day price forecasts, and support multi-market analysis.
                    </p>
                    <div style={{ display: 'flex', justifyContent: 'center', gap: '2rem', flexWrap: 'wrap', marginTop: '1.5rem' }}>
                        {[
                            { label: 'Course', value: 'Applied AI (AAI)' },
                            { label: 'Semester', value: '6th Semester' },
                            { label: 'Type', value: 'Major Project' },
                        ].map(({ label, value }) => (
                            <div key={label} style={{ textAlign: 'center' }}>
                                <p style={{ fontSize: '0.65rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.1em', color: '#64748b' }}>{label}</p>
                                <p style={{ fontSize: '0.95rem', fontWeight: 600, color: '#e2e8f0', marginTop: '0.25rem' }}>{value}</p>
                            </div>
                        ))}
                    </div>
                </div>

                {/* ═══════════ SLIDE 2 — Problem Statement ═══════════ */}
                <div className="card fade-in-up" style={{ padding: '2.5rem', maxWidth: '56rem', margin: '0 auto', width: '100%' }}>
                    <SlideBadge number={2} />
                    <CardHeader
                        icon={Lightbulb}
                        title="Problem Statement"
                        color="#f59e0b"
                    />
                    <div style={{
                        background: 'rgba(245,158,11,0.05)',
                        border: '1px solid rgba(245,158,11,0.12)',
                        borderRadius: '0.75rem',
                        padding: '1.5rem',
                        borderLeft: '3px solid #f59e0b',
                    }}>
                        <p style={{ fontSize: '1rem', color: '#cbd5e1', lineHeight: 1.9 }}>
                            Stock market prediction is a challenging problem due to the <strong style={{ color: '#f1f5f9' }}>non-linear, volatile, and noisy nature</strong> of financial data. Traditional analysis methods rely heavily on manual interpretation of indicators and are time-consuming.
                        </p>
                        <p style={{ fontSize: '1rem', color: '#cbd5e1', lineHeight: 1.9, marginTop: '1rem' }}>
                            This project addresses the challenge by building an <strong style={{ color: '#f1f5f9' }}>intelligent, automated system</strong> that leverages deep learning (LSTM) for sequential pattern recognition and gradient boosting (XGBoost) for feature-based classification — combined into an <strong style={{ color: '#f1f5f9' }}>ensemble model</strong> that predicts stock price direction with probabilistic confidence scores.
                        </p>
                    </div>
                </div>

                {/* ═══════════ SLIDE 3 — Objectives ═══════════ */}
                <div className="card fade-in-up" style={{ padding: '2.5rem', maxWidth: '56rem', margin: '0 auto', width: '100%' }}>
                    <SlideBadge number={3} />
                    <CardHeader
                        icon={Target}
                        title="Project Objectives"
                        color="#10b981"
                    />
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
                        {objectives.map(({ icon: Icon, text }, i) => (
                            <div key={i} style={{
                                display: 'flex',
                                gap: '1rem',
                                alignItems: 'flex-start',
                                background: '#0B0F19',
                                border: '1px solid #1e293b',
                                borderRadius: '0.75rem',
                                padding: '1.25rem',
                                transition: 'border-color 0.2s',
                            }}
                                onMouseEnter={e => e.currentTarget.style.borderColor = 'rgba(16,185,129,0.3)'}
                                onMouseLeave={e => e.currentTarget.style.borderColor = '#1e293b'}
                            >
                                <div style={{
                                    width: '2rem',
                                    height: '2rem',
                                    borderRadius: '0.5rem',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    background: 'rgba(16,185,129,0.1)',
                                    flexShrink: 0,
                                    marginTop: '0.125rem',
                                }}>
                                    <Icon size={14} style={{ color: '#34d399' }} />
                                </div>
                                <p style={{ fontSize: '0.875rem', color: '#cbd5e1', lineHeight: 1.7 }}>{text}</p>
                            </div>
                        ))}
                    </div>
                </div>

                {/* ═══════════ SLIDE 4 — System Architecture ═══════════ */}
                <div className="card fade-in-up" style={{ padding: '2.5rem', maxWidth: '56rem', margin: '0 auto', width: '100%' }}>
                    <SlideBadge number={4} />
                    <CardHeader
                        icon={BookOpen}
                        title="System Architecture & Pipeline"
                        subtitle="End-to-end data flow from ingestion to visualization"
                        color="#818cf8"
                    />
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0' }}>
                        {pipelineSteps.map(({ step, title, desc, icon: Icon, color }, i) => (
                            <div key={step}>
                                <div style={{ display: 'flex', gap: '1.25rem', alignItems: 'flex-start' }}>
                                    {/* Step connector */}
                                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flexShrink: 0 }}>
                                        <div style={{
                                            width: '2.75rem',
                                            height: '2.75rem',
                                            borderRadius: '50%',
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'center',
                                            background: `${color}15`,
                                            border: `2px solid ${color}40`,
                                        }}>
                                            <Icon size={16} style={{ color }} />
                                        </div>
                                        {i < pipelineSteps.length - 1 && (
                                            <div style={{
                                                width: '2px',
                                                height: '2rem',
                                                background: 'linear-gradient(to bottom, #1e293b, transparent)',
                                            }} />
                                        )}
                                    </div>
                                    {/* Content */}
                                    <div style={{ paddingBottom: i < pipelineSteps.length - 1 ? '0.5rem' : 0 }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.375rem' }}>
                                            <span style={{
                                                fontSize: '0.65rem',
                                                fontWeight: 700,
                                                fontFamily: 'var(--font-mono)',
                                                color: color,
                                                background: `${color}15`,
                                                padding: '0.125rem 0.5rem',
                                                borderRadius: '0.25rem',
                                            }}>
                                                STEP {step}
                                            </span>
                                            <h3 style={{ fontSize: '1rem', fontWeight: 600, color: '#e2e8f0' }}>{title}</h3>
                                        </div>
                                        <p style={{ fontSize: '0.875rem', color: '#94a3b8', lineHeight: 1.7 }}>{desc}</p>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* ═══════════ SLIDE 5 — ML Models Deep Dive ═══════════ */}
                <div className="card fade-in-up" style={{ padding: '2.5rem', maxWidth: '56rem', margin: '0 auto', width: '100%' }}>
                    <SlideBadge number={5} />
                    <CardHeader
                        icon={Brain}
                        title="Machine Learning Models"
                        subtitle="Dual-model ensemble architecture for robust predictions"
                        color="#ec4899"
                    />
                    <div style={{ display: 'flex', gap: '1.25rem', flexWrap: 'wrap' }}>
                        {/* LSTM Card */}
                        <div style={{
                            flex: 1,
                            minWidth: '250px',
                            background: '#0B0F19',
                            border: '1px solid rgba(139,92,246,0.2)',
                            borderRadius: '0.75rem',
                            padding: '1.5rem',
                        }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
                                <Brain size={20} style={{ color: '#8b5cf6' }} />
                                <h3 style={{ fontSize: '1.05rem', fontWeight: 600, color: '#f1f5f9' }}>LSTM Network</h3>
                            </div>
                            <p style={{ fontSize: '0.8rem', color: '#818cf8', fontWeight: 600, marginBottom: '0.75rem' }}>Deep Learning — Sequential Patterns</p>
                            <ul style={{ listStyle: 'none', padding: 0, display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                                {[
                                    'Bidirectional LSTM (128 units)',
                                    'LSTM layer (64 units)',
                                    'Dropout regularization (30%)',
                                    'Dense layers with ReLU + Sigmoid',
                                    '60-day lookback window',
                                    'Binary classification (Up/Down)',
                                    'EarlyStopping + ReduceLROnPlateau',
                                ].map((item, i) => (
                                    <li key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                        <ChevronRight size={12} style={{ color: '#8b5cf6', flexShrink: 0 }} />
                                        <span style={{ fontSize: '0.8rem', color: '#cbd5e1' }}>{item}</span>
                                    </li>
                                ))}
                            </ul>
                        </div>

                        {/* XGBoost Card */}
                        <div style={{
                            flex: 1,
                            minWidth: '250px',
                            background: '#0B0F19',
                            border: '1px solid rgba(16,185,129,0.2)',
                            borderRadius: '0.75rem',
                            padding: '1.5rem',
                        }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
                                <Cpu size={20} style={{ color: '#10b981' }} />
                                <h3 style={{ fontSize: '1.05rem', fontWeight: 600, color: '#f1f5f9' }}>XGBoost</h3>
                            </div>
                            <p style={{ fontSize: '0.8rem', color: '#34d399', fontWeight: 600, marginBottom: '0.75rem' }}>Gradient Boosting — Feature Importance</p>
                            <ul style={{ listStyle: 'none', padding: 0, display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                                {[
                                    '200 estimators, max depth 5',
                                    'Learning rate: 0.05',
                                    'Subsample: 0.9, colsample: 0.9',
                                    'L1 + L2 regularization',
                                    'Binary logistic objective',
                                    'Feature-based (single timestamp)',
                                    'Optional GridSearchCV tuning',
                                ].map((item, i) => (
                                    <li key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                        <ChevronRight size={12} style={{ color: '#10b981', flexShrink: 0 }} />
                                        <span style={{ fontSize: '0.8rem', color: '#cbd5e1' }}>{item}</span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    </div>

                    {/* Ensemble section */}
                    <div style={{
                        marginTop: '1.25rem',
                        background: 'rgba(129,140,248,0.05)',
                        border: '1px solid rgba(129,140,248,0.15)',
                        borderRadius: '0.75rem',
                        padding: '1.25rem',
                        textAlign: 'center',
                    }}>
                        <Layers size={18} style={{ color: '#818cf8', margin: '0 auto 0.5rem' }} />
                        <p style={{ fontSize: '0.9rem', fontWeight: 600, color: '#e2e8f0' }}>Ensemble Strategy</p>
                        <p style={{ fontSize: '0.8rem', color: '#94a3b8', marginTop: '0.25rem' }}>
                            Probabilities from both models are averaged to produce a final prediction with combined confidence scores.
                        </p>
                    </div>
                </div>

                {/* ═══════════ SLIDE 6 — 30-Day Forecast ═══════════ */}
                <div className="card fade-in-up" style={{ padding: '2.5rem', maxWidth: '56rem', margin: '0 auto', width: '100%' }}>
                    <SlideBadge number={6} />
                    <CardHeader
                        icon={Calendar}
                        title="30-Day Price Forecast"
                        subtitle="Monte Carlo simulation based forecasting methodology"
                        color="#f59e0b"
                    />
                    <div style={{
                        background: '#0B0F19',
                        border: '1px solid #1e293b',
                        borderRadius: '0.75rem',
                        padding: '1.5rem',
                    }}>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
                            {[
                                { label: 'Simulation Method', value: 'Monte Carlo (100 paths)', color: '#818cf8' },
                                { label: 'Forecast Window', value: '30 trading days', color: '#f59e0b' },
                                { label: 'Confidence Bands', value: '20th–80th percentile', color: '#10b981' },
                                { label: 'Drift Factors', value: 'RSI, MACD, SMA crossover', color: '#ec4899' },
                                { label: 'Volatility Model', value: '20-day historical rolling', color: '#ef4444' },
                                { label: 'Mean Reversion', value: 'Pull toward SMA-50 after day 10', color: '#8b5cf6' },
                            ].map(({ label, value, color }) => (
                                <div key={label} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                    <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: color, flexShrink: 0 }} />
                                    <div>
                                        <p style={{ fontSize: '0.7rem', fontWeight: 500, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</p>
                                        <p style={{ fontSize: '0.875rem', fontWeight: 600, color: '#e2e8f0' }}>{value}</p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>

                {/* ═══════════ SLIDE 7 — Feature Engineering ═══════════ */}
                <div className="card fade-in-up" style={{ padding: '2.5rem', maxWidth: '56rem', margin: '0 auto', width: '100%' }}>
                    <SlideBadge number={7} />
                    <CardHeader
                        icon={Database}
                        title="Feature Engineering"
                        subtitle="29 technical indicators computed from raw OHLCV data"
                        color="#3b82f6"
                    />
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
                        {features.map(({ name, type, desc }) => (
                            <div key={name} style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '1rem',
                                padding: '0.75rem 1rem',
                                background: '#0B0F19',
                                border: '1px solid #1e293b',
                                borderRadius: '0.5rem',
                                transition: 'border-color 0.2s',
                            }}
                                onMouseEnter={e => e.currentTarget.style.borderColor = '#334155'}
                                onMouseLeave={e => e.currentTarget.style.borderColor = '#1e293b'}
                            >
                                <span style={{
                                    fontSize: '0.6rem',
                                    fontWeight: 700,
                                    textTransform: 'uppercase',
                                    letterSpacing: '0.05em',
                                    padding: '0.2rem 0.5rem',
                                    borderRadius: '0.25rem',
                                    background: `${typeColors[type]}15`,
                                    color: typeColors[type],
                                    flexShrink: 0,
                                    minWidth: '70px',
                                    textAlign: 'center',
                                }}>
                                    {type}
                                </span>
                                <div style={{ flex: 1 }}>
                                    <span style={{ fontSize: '0.875rem', fontWeight: 600, color: '#e2e8f0', fontFamily: 'var(--font-mono)' }}>{name}</span>
                                    <span style={{ fontSize: '0.8rem', color: '#64748b', marginLeft: '0.75rem' }}>— {desc}</span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* ═══════════ SLIDE 8 — Tech Stack ═══════════ */}
                <div className="card fade-in-up" style={{ padding: '2.5rem', maxWidth: '56rem', margin: '0 auto', width: '100%' }}>
                    <SlideBadge number={8} />
                    <CardHeader
                        icon={GitBranch}
                        title="Technology Stack"
                        color="#8b5cf6"
                    />
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
                        {techStack.map(({ icon: Icon, name, desc, category }) => (
                            <div key={name} style={{
                                background: '#0B0F19',
                                border: '1px solid #1e293b',
                                borderRadius: '0.75rem',
                                padding: '1.25rem',
                                display: 'flex',
                                gap: '1rem',
                                alignItems: 'flex-start',
                                transition: 'border-color 0.2s, transform 0.2s',
                            }}
                                onMouseEnter={e => { e.currentTarget.style.borderColor = '#334155'; e.currentTarget.style.transform = 'translateY(-2px)' }}
                                onMouseLeave={e => { e.currentTarget.style.borderColor = '#1e293b'; e.currentTarget.style.transform = 'translateY(0)' }}
                            >
                                <div style={{
                                    padding: '0.5rem',
                                    borderRadius: '0.5rem',
                                    background: 'rgba(139,92,246,0.1)',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    flexShrink: 0,
                                }}>
                                    <Icon size={16} style={{ color: '#a78bfa' }} />
                                </div>
                                <div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                        <h3 style={{ fontSize: '0.875rem', fontWeight: 600, color: '#e2e8f0' }}>{name}</h3>
                                        <span style={{
                                            fontSize: '0.55rem',
                                            fontWeight: 600,
                                            textTransform: 'uppercase',
                                            letterSpacing: '0.05em',
                                            padding: '0.125rem 0.375rem',
                                            borderRadius: '0.25rem',
                                            background: 'rgba(100,116,139,0.15)',
                                            color: '#64748b',
                                        }}>
                                            {category}
                                        </span>
                                    </div>
                                    <p style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.25rem' }}>{desc}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* ═══════════ SLIDE 9 — Key Numbers ═══════════ */}
                <div className="card fade-in-up" style={{ padding: '2.5rem', maxWidth: '56rem', margin: '0 auto', width: '100%' }}>
                    <SlideBadge number={9} />
                    <CardHeader
                        icon={BarChart3}
                        title="Key Numbers"
                        color="#10b981"
                    />
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
                        {keyResults.map(({ label, value, suffix }) => (
                            <div key={label} style={{
                                background: '#0B0F19',
                                border: '1px solid #1e293b',
                                borderRadius: '0.75rem',
                                padding: '1.5rem',
                                textAlign: 'center',
                            }}>
                                <p style={{
                                    fontSize: '2.25rem',
                                    fontWeight: 700,
                                    fontFamily: 'var(--font-mono)',
                                    background: 'linear-gradient(135deg, #818cf8, #34d399)',
                                    WebkitBackgroundClip: 'text',
                                    WebkitTextFillColor: 'transparent',
                                    lineHeight: 1,
                                }}>
                                    {value}
                                </p>
                                <p style={{ fontSize: '0.8rem', fontWeight: 600, color: '#e2e8f0', marginTop: '0.5rem' }}>{label}</p>
                                <p style={{ fontSize: '0.7rem', color: '#64748b', marginTop: '0.125rem' }}>{suffix}</p>
                            </div>
                        ))}
                    </div>
                </div>

                {/* ═══════════ SLIDE 10 — Future Scope ═══════════ */}
                <div className="card fade-in-up" style={{ padding: '2.5rem', maxWidth: '56rem', margin: '0 auto', width: '100%' }}>
                    <SlideBadge number={10} />
                    <CardHeader
                        icon={Sparkles}
                        title="Future Scope"
                        subtitle="Planned enhancements and upcoming features"
                        color="#f59e0b"
                    />
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
                        {futureScope.map(({ icon: Icon, title, desc }) => (
                            <div key={title} style={{
                                background: '#0B0F19',
                                border: '1px solid #1e293b',
                                borderRadius: '0.75rem',
                                padding: '1.5rem',
                                transition: 'border-color 0.2s',
                            }}
                                onMouseEnter={e => e.currentTarget.style.borderColor = 'rgba(245,158,11,0.3)'}
                                onMouseLeave={e => e.currentTarget.style.borderColor = '#1e293b'}
                            >
                                <div style={{
                                    width: '2.25rem',
                                    height: '2.25rem',
                                    borderRadius: '0.5rem',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    background: 'rgba(245,158,11,0.1)',
                                    marginBottom: '0.75rem',
                                }}>
                                    <Icon size={16} style={{ color: '#f59e0b' }} />
                                </div>
                                <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: '#e2e8f0', marginBottom: '0.375rem' }}>{title}</h3>
                                <p style={{ fontSize: '0.8rem', color: '#94a3b8', lineHeight: 1.6 }}>{desc}</p>
                            </div>
                        ))}
                    </div>
                </div>

                {/* ═══════════ Disclaimer ═══════════ */}
                <div style={{ textAlign: 'center', maxWidth: '36rem', margin: '0 auto', padding: '1rem 0' }}>
                    <p style={{ fontSize: '0.75rem', color: '#475569', lineHeight: 1.7 }}>
                        <strong style={{ color: '#64748b', fontWeight: 600 }}>⚠️ Disclaimer:</strong>{' '}
                        This is an academic/educational project. Predictions generated by the system should not be used as financial advice. Stock markets are inherently unpredictable. Always consult a qualified financial advisor before making investment decisions.
                    </p>
                </div>

            </div>
        </section>
    )
}
