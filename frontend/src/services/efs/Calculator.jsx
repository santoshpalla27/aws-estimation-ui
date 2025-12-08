import React, { useState, useEffect } from 'react'
import { HardDrive } from 'lucide-react'

export default function EFSCalculator({ serviceId }) {
    const [metadata, setMetadata] = useState(null)
    const [result, setResult] = useState(null)

    const [formData, setFormData] = useState({
        storageClass: 'Standard',
        location: 'US East (N. Virginia)',
        storageGB: 100
    })

    useEffect(() => {
        fetch(`/api/services/${serviceId}/metadata`)
            .then(res => res.json())
            .then(data => setMetadata(data))
            .catch(console.error)
    }, [serviceId])

    const handleEstimate = async () => {
        const res = await fetch(`/api/estimate/${serviceId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        })
        setResult(await res.json())
    }

    return (
        <div className="card">
            <div className="header">
                <h1><HardDrive size={32} style={{ marginRight: '0.5rem', marginBottom: '-6px' }} /> EFS Estimator</h1>
            </div>

            <div style={{ display: 'grid', gap: '1rem', maxWidth: '600px' }}>
                <div>
                    <label className="label">Location</label>
                    <select className="input" value={formData.location} onChange={e => setFormData({ ...formData, location: e.target.value })}>
                        {metadata?.locations?.map(opt => <option key={opt} value={opt}>{opt}</option>)}
                    </select>
                </div>

                <div>
                    <label className="label">Storage Class</label>
                    <select className="input" value={formData.storageClass} onChange={e => setFormData({ ...formData, storageClass: e.target.value })}>
                        {metadata?.storageClasses?.map(opt => <option key={opt} value={opt}>{opt}</option>)}
                    </select>
                </div>

                <div>
                    <label className="label">Storage (GB)</label>
                    <input
                        type="number" className="input"
                        value={formData.storageGB}
                        onChange={e => setFormData({ ...formData, storageGB: parseFloat(e.target.value) })}
                    />
                </div>

                <button className="btn" onClick={handleEstimate}>Calculate Cost</button>
            </div>

            {result && (
                <div style={{ marginTop: '2rem', padding: '1rem', background: 'var(--bg-secondary)', borderRadius: 'var(--radius)' }}>
                    <h3>Estimated Cost</h3>
                    <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>
                        ${result.total_cost?.toFixed(2)} / month
                    </div>
                </div>
            )}
        </div>
    )
}
