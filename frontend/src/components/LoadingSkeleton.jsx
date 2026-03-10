export default function LoadingSkeleton() {
    return (
        <div className="fade-in-up" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {/* Ensemble skeleton */}
            <div className="card" style={{ padding: '2rem' }}>
                <div className="skeleton" style={{ width: '140px', height: '12px', marginBottom: '16px' }} />
                <div className="skeleton" style={{ width: '180px', height: '36px', marginBottom: '12px' }} />
                <div className="skeleton" style={{ width: '100%', height: '24px', marginBottom: '8px' }} />
                <div className="skeleton" style={{ width: '60%', height: '14px' }} />
            </div>

            {/* Model cards skeleton */}
            <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                {[1, 2].map((i) => (
                    <div key={i} className="card" style={{ flex: 1, minWidth: '250px', padding: '1.5rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
                            <div className="skeleton" style={{ width: '36px', height: '36px', borderRadius: '8px' }} />
                            <div>
                                <div className="skeleton" style={{ width: '80px', height: '12px', marginBottom: '6px' }} />
                                <div className="skeleton" style={{ width: '100px', height: '10px' }} />
                            </div>
                        </div>
                        <div className="skeleton" style={{ width: '100px', height: '28px', marginBottom: '16px' }} />
                        <div className="skeleton" style={{ width: '100%', height: '6px', marginBottom: '12px' }} />
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                            <div className="skeleton" style={{ flex: 1, height: '44px', borderRadius: '8px' }} />
                            <div className="skeleton" style={{ flex: 1, height: '44px', borderRadius: '8px' }} />
                        </div>
                    </div>
                ))}
            </div>

            {/* Chart skeleton */}
            <div className="card" style={{ padding: '1.5rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
                    <div>
                        <div className="skeleton" style={{ width: '80px', height: '16px', marginBottom: '8px' }} />
                        <div className="skeleton" style={{ width: '140px', height: '24px' }} />
                    </div>
                    <div className="skeleton" style={{ width: '180px', height: '28px', borderRadius: '8px' }} />
                </div>
                <div className="skeleton" style={{ width: '100%', height: '340px', borderRadius: '8px' }} />
            </div>
        </div>
    )
}
