import React, { useState } from 'react'
import { Plus, X } from 'lucide-react'

// Mocking simple Architecture Builder for demo
// In a full implementation, this might use React Flow or similar
export default function ArchitectureBuilder({ services }) {
    const [nodes, setNodes] = useState([])
    const [totalCost, setTotalCost] = useState(0)

    const addNode = (serviceId) => {
        const service = services.find(s => s.serviceId === serviceId)
        setNodes([...nodes, {
            id: Date.now(),
            serviceId,
            label: service.label,
            cost: 0,
            config: {}
        }])
        // In real app, we would open config modal immediately
    }

    const removeNode = (id) => {
        setNodes(nodes.filter(n => n.id !== id))
        recalculateParams()
    }

    // Placeholder for recalculation
    const recalculateParams = () => {
        // Sum costs
        const total = nodes.reduce((acc, node) => acc + (node.cost || 0), 0)
        setTotalCost(total)
    }

    return (
        <div className="card">
            <div className="header">
                <h1>Architecture Builder</h1>
            </div>

            <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem' }}>
                <div style={{ width: '200px', borderRight: '1px solid var(--border)', paddingRight: '1rem' }}>
                    <h3>Toolbox</h3>
                    {services?.map(s => (
                        <div
                            key={s.serviceId}
                            className="service-item"
                            onClick={() => addNode(s.serviceId)}
                        >
                            <Plus size={16} /> {s.label}
                        </div>
                    ))}
                </div>

                <div style={{ flex: 1, minHeight: '400px', background: 'var(--bg-primary)', borderRadius: 'var(--radius)', padding: '1rem', position: 'relative' }}>
                    {nodes.length === 0 && (
                        <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', color: 'var(--text-secondary)' }}>
                            Click services to add nodes
                        </div>
                    )}

                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem' }}>
                        {nodes.map(node => (
                            <div key={node.id} className="card" style={{ width: '200px', padding: '1rem' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                                    <strong>{node.label}</strong>
                                    <X size={16} style={{ cursor: 'pointer' }} onClick={() => removeNode(node.id)} />
                                </div>
                                <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                                    Cost: ${node.cost}
                                </div>
                                <button className="btn" style={{ fontSize: '0.8rem', marginTop: '0.5rem', padding: '0.3rem 0.5rem', width: '100%' }}>
                                    Configure
                                </button>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            <div style={{ borderTop: '1px solid var(--border)', paddingTop: '1rem', display: 'flex', justifyContent: 'flex-end' }}>
                <h2>Total Estimated Cost: ${totalCost.toFixed(2)}/mo</h2>
            </div>
        </div>
    )
}
