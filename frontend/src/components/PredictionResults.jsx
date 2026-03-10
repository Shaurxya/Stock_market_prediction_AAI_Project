import { TrendingUp, TrendingDown, Brain, Cpu, Layers, Target } from 'lucide-react'

function ConfidenceBar({ value, color }) {
    return (
        <div className="confidence-bar-bg" style={{ marginTop: '0.5rem' }}>
            <div
                className="confidence-bar-fill"
                style={{
                    width: `${(value * 100).toFixed(0)}%`,
                    background: color,
                }}
            />
        </div>
    )
}

function ModelCard({ model, prediction, confidence, probabilityUp, probabilityDown, icon: Icon, delay }) {
    const isUp = prediction === 'Up'
    const color = isUp ? '#10b981' : '#f43f5e'

    return (
        <div className={`card fade-in-up fade-in-up-delay-${delay}`}
            style={{ flex: 1, minWidth: '250px', padding: '1.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
                <div style={{
                    width: '2.25rem',
                    height: '2.25rem',
                    borderRadius: '0.5rem',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background: isUp ? 'rgba(16,185,129,0.1)' : 'rgba(244,63,94,0.1)',
                }}>
                    <Icon size={18} style={{ color }} />
                </div>
                <div>
                    <h3 style={{ fontSize: '0.875rem', fontWeight: 600, color: '#f1f5f9' }}>{model}</h3>
                    <p style={{ fontSize: '0.75rem', color: '#64748b' }}>Model Prediction</p>
                </div>
            </div>

            {/* Prediction */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
                {isUp ? <TrendingUp size={24} color="#10b981" /> : <TrendingDown size={24} color="#f43f5e" />}
                <span style={{ fontSize: '1.5rem', fontWeight: 700, color }}>{prediction}</span>
            </div>

            {/* Confidence */}
            <div style={{ marginBottom: '0.75rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '0.75rem', color: '#64748b' }}>Confidence</span>
                    <span style={{ fontSize: '0.875rem', fontWeight: 600, fontFamily: 'var(--font-mono)', color }}>
                        {(confidence * 100).toFixed(1)}%
                    </span>
                </div>
                <ConfidenceBar value={confidence} color={color} />
            </div>

            {/* Probabilities */}
            <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem', paddingTop: '0.75rem', borderTop: '1px solid #1e293b' }}>
                <div style={{ flex: 1, textAlign: 'center', padding: '0.5rem', borderRadius: '0.5rem', background: 'rgba(16, 185, 129, 0.05)' }}>
                    <p style={{ fontSize: '0.625rem', fontWeight: 500, color: '#64748b' }}>P(Up)</p>
                    <p style={{ fontSize: '0.875rem', fontWeight: 600, color: '#34d399', fontFamily: 'var(--font-mono)' }}>
                        {(probabilityUp * 100).toFixed(1)}%
                    </p>
                </div>
                <div style={{ flex: 1, textAlign: 'center', padding: '0.5rem', borderRadius: '0.5rem', background: 'rgba(244, 63, 94, 0.05)' }}>
                    <p style={{ fontSize: '0.625rem', fontWeight: 500, color: '#64748b' }}>P(Down)</p>
                    <p style={{ fontSize: '0.875rem', fontWeight: 600, color: '#fb7185', fontFamily: 'var(--font-mono)' }}>
                        {(probabilityDown * 100).toFixed(1)}%
                    </p>
                </div>
            </div>
        </div>
    )
}

export default function PredictionResults({ data }) {
    if (!data) return null

    const { predictions, ensemble_prediction, ensemble_confidence, forecast_prices, current_price, company_name, ticker, currency } = data

    const isEnsUp = ensemble_prediction === 'Up'
    const ensColor = isEnsUp ? '#10b981' : '#f43f5e'
    const currencySymbol = currency === 'INR' ? '₹' : '$'

    const modelIcons = { 'LSTM': Brain, 'XGBoost': Cpu }

    return (
        <div className="fade-in-up">
            {/* Ensemble Result */}
            <div className="card" style={{ marginBottom: '1rem', padding: '2rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                    <Layers size={15} style={{ color: '#818cf8' }} />
                    <span style={{ fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.1em', color: '#818cf8' }}>
                        Ensemble Prediction
                    </span>
                </div>

                <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
                    <div>
                        <h2 style={{ fontSize: '1rem', fontWeight: 500, color: '#94a3b8' }}>
                            {company_name || ticker}
                        </h2>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginTop: '0.25rem' }}>
                            {isEnsUp ? <TrendingUp size={32} color="#10b981" /> : <TrendingDown size={32} color="#f43f5e" />}
                            <span style={{ fontSize: '2rem', fontWeight: 700, color: ensColor }}>
                                {ensemble_prediction}
                            </span>
                        </div>
                    </div>

                    <div style={{ marginLeft: 'auto', textAlign: 'right' }}>
                        <p style={{ fontSize: '0.75rem', color: '#64748b' }}>Current Price</p>
                        <p style={{ fontSize: '1.5rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: '#f1f5f9' }}>
                            {currencySymbol}{current_price?.toFixed(2)}
                        </p>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', justifyContent: 'flex-end', marginTop: '0.25rem' }}>
                            <Target size={13} style={{ color: ensColor }} />
                            <span style={{ fontSize: '0.875rem', fontWeight: 600, color: ensColor, fontFamily: 'var(--font-mono)' }}>
                                {(ensemble_confidence * 100).toFixed(1)}% confidence
                            </span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Individual Model Cards */}
            <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                {predictions?.map((pred, i) => (
                    <ModelCard
                        key={pred.model}
                        model={pred.model}
                        prediction={pred.prediction}
                        confidence={pred.confidence}
                        probabilityUp={pred.probability_up}
                        probabilityDown={pred.probability_down}
                        icon={modelIcons[pred.model] || Brain}
                        delay={i + 2}
                    />
                ))}
            </div>

            {/* Market Data */}
            {data.market_data && (
                <div className="card fade-in-up fade-in-up-delay-4" style={{ marginTop: '1rem', padding: '1.25rem' }}>
                    <h3 style={{ fontSize: '0.875rem', fontWeight: 600, marginBottom: '0.75rem', color: '#f1f5f9' }}>
                        Market Information
                    </h3>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem' }}>
                        {[
                            { label: 'Sector', value: data.market_data.sector },
                            { label: 'P/E Ratio', value: data.market_data.pe_ratio ? data.market_data.pe_ratio.toFixed(2) : 'N/A' },
                            { label: '52W High', value: data.market_data['52w_high'] ? `${currencySymbol}${data.market_data['52w_high'].toFixed(2)}` : 'N/A' },
                            { label: '52W Low', value: data.market_data['52w_low'] ? `${currencySymbol}${data.market_data['52w_low'].toFixed(2)}` : 'N/A' },
                        ].map(({ label, value }) => (
                            <div key={label}>
                                <p style={{ fontSize: '0.625rem', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#64748b' }}>{label}</p>
                                <p style={{ fontSize: '0.875rem', fontWeight: 600, marginTop: '0.125rem', color: '#f1f5f9', fontFamily: 'var(--font-mono)' }}>
                                    {value || 'N/A'}
                                </p>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    )
}
