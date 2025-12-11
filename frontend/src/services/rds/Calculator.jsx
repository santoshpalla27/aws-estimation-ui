import React, { useState, useEffect } from 'react'
import { Database } from 'lucide-react'

export default function RDSCalculator({ serviceId }) {
    const [metadata, setMetadata] = useState(null)
    const [result, setResult] = useState(null)

    const [formData, setFormData] = useState({
        instanceType: 'db.t3.micro',
        databaseEngine: 'MySQL',
        location: 'US East (N. Virginia)',
        deploymentOption: 'Single-AZ',
        hours: 730
    })

    useEffect(() => {
        fetch(`/api/pricing/metadata/${serviceId}`)
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
                <h1><Database size={32} style={{ marginRight: '0.5rem', marginBottom: '-6px' }} /> RDS Estimator</h1>
            </div>

            <div style={{ display: 'grid', gap: '1rem', maxWidth: '600px' }}>
                <div>
                    <label className="label">Location</label>
                    <select className="input" value={formData.location} onChange={e => setFormData({ ...formData, location: e.target.value })}>
                        {metadata?.locations?.map(opt => <option key={opt} value={opt}>{opt}</option>)}
                    </select>
                </div>

                <div>
                    <label className="label">Database Engine</label>
                    <select className="input" value={formData.databaseEngine} onChange={e => setFormData({ ...formData, databaseEngine: e.target.value })}>
                        {metadata?.databaseEngines?.map(opt => <option key={opt} value={opt}>{opt}</option>)}
                    </select>
                </div>

                <div>
                    <label className="label">Instance Type</label>
                    <select className="input" value={formData.instanceType} onChange={e => setFormData({ ...formData, instanceType: e.target.value })}>
                        {metadata?.instanceTypes?.map(opt => <option key={opt} value={opt}>{opt}</option>)}
                    </select>
                </div>

                <div>
                    <label className="label">Deployment</label>
                    <select className="input" value={formData.deploymentOption} onChange={e => setFormData({ ...formData, deploymentOption: e.target.value })}>
                        <option value="Single-AZ">Single-AZ</option>
                        <option value="Multi-AZ">Multi-AZ</option>
                    </select>
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
