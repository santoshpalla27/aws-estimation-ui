import React, { useState, useEffect } from 'react'
import { Server } from 'lucide-react'

export default function EC2Calculator({ serviceId }) {
    const [metadata, setMetadata] = useState(null)
    const [loading, setLoading] = useState(true)
    const [result, setResult] = useState(null)

    const [formData, setFormData] = useState({
        instanceType: 't3.micro', // Default or from metadata
        location: 'US East (N. Virginia)',
        operatingSystem: 'Linux',
        hours: 730,
        count: 1
    })

    useEffect(() => {
        fetch(`/api/services/${serviceId}/metadata`)
            .then(res => res.json())
            .then(data => {
                setMetadata(data)
                setLoading(false)
                // Set defaults if available
                if (data.instanceTypes && data.instanceTypes.length > 0) {
                    setFormData(prev => ({ ...prev, instanceType: data.instanceTypes[0] }))
                }
            })
            .catch(err => {
                console.error("Failed to load metadata", err)
                setLoading(false)
            })
    }, [serviceId])

    const handleEstimate = async () => {
        try {
            const res = await fetch(`/api/estimate/${serviceId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            })
            const data = await res.json()
            setResult(data)
        } catch (e) {
            console.error("Estimation failed", e)
        }
    }

    if (loading) return <div>Loading metadata...</div>

    return (
        <div className="card">
            <div className="header">
                <h1><Server size={32} style={{ marginRight: '0.5rem', marginBottom: '-6px' }} /> EC2 Estimator</h1>
            </div>

            <div style={{ display: 'grid', gap: '1rem', maxWidth: '600px' }}>
                <div>
                    <label className="label">Location</label>
                    <select
                        className="input"
                        value={formData.location}
                        onChange={e => setFormData({ ...formData, location: e.target.value })}
                    >
                        {metadata?.locations?.map(opt => (
                            <option key={opt} value={opt}>{opt}</option>
                        ))}
                    </select>
                </div>

                <div>
                    <label className="label">Instance Type</label>
                    <select
                        className="input"
                        value={formData.instanceType}
                        onChange={e => setFormData({ ...formData, instanceType: e.target.value })}
                    >
                        {metadata?.instanceTypes?.map(opt => (
                            <option key={opt} value={opt}>{opt}</option>
                        ))}
                    </select>
                </div>

                <div>
                    <label className="label">Operating System</label>
                    <select
                        className="input"
                        value={formData.operatingSystem}
                        onChange={e => setFormData({ ...formData, operatingSystem: e.target.value })}
                    >
                        {metadata?.operatingSystems?.map(opt => (
                            <option key={opt} value={opt}>{opt}</option>
                        ))}
                    </select>
                </div>

                <div style={{ display: 'flex', gap: '1rem' }}>
                    <div style={{ flex: 1 }}>
                        <label className="label">Count</label>
                        <input
                            type="number"
                            className="input"
                            value={formData.count}
                            onChange={e => setFormData({ ...formData, count: parseInt(e.target.value) })}
                            min="1"
                        />
                    </div>
                    <div style={{ flex: 1 }}>
                        <label className="label">Hours/Month</label>
                        <input
                            type="number"
                            className="input"
                            value={formData.hours}
                            onChange={e => setFormData({ ...formData, hours: parseFloat(e.target.value) })}
                            max="744"
                        />
                    </div>
                </div>

                <button className="btn" onClick={handleEstimate} style={{ marginTop: '1rem' }}>
                    Calculate Cost
                </button>
            </div>

            {result && (
                <div style={{ marginTop: '2rem', padding: '1rem', background: 'var(--bg-secondary)', borderRadius: 'var(--radius)' }}>
                    <h3>Estimated Cost</h3>
                    <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>
                        ${result.total_cost?.toFixed(2)} <span style={{ fontSize: '1rem', color: 'var(--text-secondary)' }}>/ month</span>
                    </div>
                    {result.breakdown && (
                        <div style={{ marginTop: '0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                            Unit Price: ${result.breakdown.unit_price} x {result.breakdown.count} instance(s) x {result.breakdown.hours} hours
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}
