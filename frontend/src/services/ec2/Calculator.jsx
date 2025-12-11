import React, { useState, useEffect } from 'react'
import { Server, HardDrive, Cpu, Zap } from 'lucide-react'

export default function EC2Calculator({ serviceId }) {
    const [metadata, setMetadata] = useState(null)
    const [loading, setLoading] = useState(true)
    const [result, setResult] = useState(null)

    // UI State
    const [selectedInstanceSpecs, setSelectedInstanceSpecs] = useState(null)

    const [formData, setFormData] = useState({
        instanceType: 't3.micro', // Default or from metadata
        location: 'US East (N. Virginia)',
        operatingSystem: 'Linux',
        hours: 730,
        count: 1,
        // Storage
        storageSize: 30, // GB
        storageType: 'gp3'
    })

    useEffect(() => {
        fetch(`/api/pricing/metadata/${serviceId}`)
            .then(res => res.json())
            .then(data => {
                setMetadata(data)
                setLoading(false)

                // Set defaults if available
                if (data.instanceTypes && data.instanceTypes.length > 0) {
                    const defaultType = data.instanceTypes[0]
                    setFormData(prev => ({ ...prev, instanceType: defaultType }))
                    updateSpecs(defaultType, data)
                }
            })
            .catch(err => {
                console.error("Failed to load metadata", err)
                setLoading(false)
            })
    }, [serviceId])

    const updateSpecs = (type, metaData = metadata) => {
        if (metaData && metaData.instanceTypeDetails) {
            const specs = metaData.instanceTypeDetails.find(d => d.instanceType === type)
            setSelectedInstanceSpecs(specs)
        }
    }

    // Derived State
    const [availableStorageTypes, setAvailableStorageTypes] = useState([])

    useEffect(() => {
        if (metadata && metadata.storagePrices && metadata.storagePrices[formData.location]) {
            const types = Object.keys(metadata.storagePrices[formData.location])
            setAvailableStorageTypes(types)
            if (types.length > 0 && !types.includes(formData.storageType)) {
                setFormData(prev => ({ ...prev, storageType: types[0] }))
            }
        }
    }, [metadata, formData.location])

    const handleInstanceChange = (e) => {
        const type = e.target.value
        setFormData({ ...formData, instanceType: type })
        updateSpecs(type)
    }

    const handleEstimate = async () => {
        try {
            // Get Base Compute Cost
            const res = await fetch(`/api/estimate/${serviceId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            })
            const baseData = await res.json()

            // Calculate Storage Cost
            let storageUnitCost = 0.08 // Fallback
            if (metadata && metadata.storagePrices && metadata.storagePrices[formData.location]) {
                const price = metadata.storagePrices[formData.location][formData.storageType]
                if (price) storageUnitCost = parseFloat(price)
            }

            const storageCost = formData.storageSize * storageUnitCost

            setResult({
                ...baseData,
                storage_cost: storageCost,
                total_cost: (baseData.total_cost || 0) + storageCost,
                storage_unit_price: storageUnitCost
            })
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

            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(300px, 2fr) 1fr', gap: '2rem' }}>
                {/* Left Column: Configuration */}
                <div style={{ display: 'grid', gap: '1.5rem' }}>

                    {/* Region & OS */}
                    <div className="card" style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}>
                        <h3 style={{ fontSize: '1rem', marginTop: 0 }}>Basic Configuration</h3>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
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
                        </div>
                    </div>

                    {/* Instance Selection */}
                    <div className="card" style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}>
                        <h3 style={{ fontSize: '1rem', marginTop: 0 }}>Instance Type</h3>
                        <div>
                            <select
                                className="input"
                                value={formData.instanceType}
                                onChange={handleInstanceChange}
                                style={{ marginBottom: '1rem' }}
                            >
                                {metadata?.instanceTypes?.map(opt => (
                                    <option key={opt} value={opt}>{opt}</option>
                                ))}
                            </select>

                            {selectedInstanceSpecs && (
                                <div style={{
                                    display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr',
                                    gap: '0.5rem', fontSize: '0.85rem',
                                    background: 'var(--bg)', padding: '0.75rem', borderRadius: 'var(--radius)'
                                }}>
                                    <div>
                                        <div style={{ color: 'var(--text-secondary)' }}>vCPU</div>
                                        <div style={{ fontWeight: 'bold' }}>{selectedInstanceSpecs.vcpu || '-'}</div>
                                    </div>
                                    <div>
                                        <div style={{ color: 'var(--text-secondary)' }}>Memory</div>
                                        <div style={{ fontWeight: 'bold' }}>{selectedInstanceSpecs.memory || '-'}</div>
                                    </div>
                                    <div>
                                        <div style={{ color: 'var(--text-secondary)' }}>Network</div>
                                        <div style={{ fontWeight: 'bold' }}>{selectedInstanceSpecs.networkPerformance || '-'}</div>
                                    </div>
                                    <div>
                                        <div style={{ color: 'var(--text-secondary)' }}>Includes</div>
                                        <div style={{ fontWeight: 'bold' }}>{selectedInstanceSpecs.storage || 'EBS Only'}</div>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Storage */}
                    <div className="card" style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}>
                        <h3 style={{ fontSize: '1rem', marginTop: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <HardDrive size={16} /> Storage (EBS)
                        </h3>
                        {availableStorageTypes.length === 0 ? (
                            <div style={{ padding: '1rem', background: 'var(--bg)', borderRadius: 'var(--radius)', fontSize: '0.9rem', color: 'orange' }}>
                                Values not available for this region yet. Run data pipeline update.
                            </div>
                        ) : (
                            <div style={{ display: 'flex', gap: '1rem' }}>
                                <div style={{ flex: 1 }}>
                                    <label className="label">Volume Size (GB)</label>
                                    <input
                                        type="number"
                                        className="input"
                                        value={formData.storageSize}
                                        onChange={e => setFormData({ ...formData, storageSize: parseInt(e.target.value) })}
                                        min="1"
                                    />
                                </div>
                                <div style={{ flex: 1 }}>
                                    <label className="label">Volume Type</label>
                                    <select
                                        className="input"
                                        value={formData.storageType}
                                        onChange={e => setFormData({ ...formData, storageType: e.target.value })}
                                    >
                                        {availableStorageTypes.map(t => (
                                            <option key={t} value={t}>{t}</option>
                                        ))}
                                    </select>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Usage */}
                    <div className="card" style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}>
                        <h3 style={{ fontSize: '1rem', marginTop: 0 }}>Usage</h3>
                        <div style={{ display: 'flex', gap: '1rem' }}>
                            <div style={{ flex: 1 }}>
                                <label className="label">Instance Count</label>
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
                    </div>

                    <button className="btn" onClick={handleEstimate} style={{ marginTop: '0.5rem' }}>
                        Calculate Cost
                    </button>
                </div>

                {/* Right Column: Summary */}
                <div>
                    {result ? (
                        <div style={{ position: 'sticky', top: '2rem', background: 'var(--bg-secondary)', padding: '1.5rem', borderRadius: 'var(--radius)', border: '1px solid var(--primary)' }}>
                            <h3>Estimated Cost</h3>
                            <div style={{ fontSize: '2.5rem', fontWeight: 'bold', color: 'var(--primary)' }}>
                                ${result.total_cost?.toFixed(2)} <span style={{ fontSize: '1rem', color: 'var(--text-secondary)' }}>/ mo</span>
                            </div>

                            <hr style={{ border: 0, borderTop: '1px solid var(--border)', margin: '1rem 0' }} />

                            <div style={{ fontSize: '0.9rem' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                                    <span>Compute ({formData.count} instances)</span>
                                    <span>${(result.total_cost - (result.storage_cost || 0)).toFixed(2)}</span>
                                </div>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                                    <span>Storage ({formData.storageSize} GB)</span>
                                    <span>${(result.storage_cost || 0).toFixed(2)}</span>
                                </div>
                                {result.storage_unit_price && (
                                    <div style={{ marginTop: '0.5rem', fontSize: '0.8rem', color: 'var(--text-secondary)', textAlign: 'right' }}>
                                        Storage Rate: ${result.storage_unit_price.toFixed(4)}/GB
                                    </div>
                                )}
                            </div>
                        </div>
                    ) : (
                        <div style={{ padding: '1.5rem', border: '1px dashed var(--border)', borderRadius: 'var(--radius)', textAlign: 'center', color: 'var(--text-secondary)' }}>
                            <p>Configure parameters to see estimation.</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
