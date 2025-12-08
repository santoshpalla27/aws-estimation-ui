import React, { useState, useEffect, Suspense } from 'react'
import { Layout, CheckSquare, Plus, HardDrive, Database, Server, PenTool } from 'lucide-react'
import ArchitectureBuilder from './components/ArchitectureBuilder'

// Dynamic Service Loader
const serviceCalculators = import.meta.glob('./services/*/Calculator.jsx')

function App() {
    const [activeService, setActiveService] = useState('dashboard')
    const [services, setServices] = useState([])
    const [CalculatorComponent, setCalculatorComponent] = useState(null)

    useEffect(() => {
        fetch('/api/services')
            .then(res => res.json())
            .then(data => setServices(data))
            .catch(err => console.error("Failed to load services", err))
    }, [])

    useEffect(() => {
        if (activeService === 'dashboard' || activeService === 'builder') {
            setCalculatorComponent(null)
            return
        }

        const loadComponent = async () => {
            const path = `./services/${activeService}/Calculator.jsx`
            if (serviceCalculators[path]) {
                try {
                    const mod = await serviceCalculators[path]()
                    setCalculatorComponent(() => mod.default)
                } catch (e) {
                    console.error(`Failed to load calculator for ${activeService}`, e)
                }
            }
        }
        loadComponent()
    }, [activeService])

    return (
        <div className="layout">
            <aside className="sidebar">
                <div className="header" style={{ marginBottom: '1rem' }}>
                    <h2 style={{ fontSize: '1.25rem', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <Layout size={20} /> CloudEstimator
                    </h2>
                </div>

                <div
                    className={`service-item ${activeService === 'dashboard' ? 'active' : ''}`}
                    onClick={() => setActiveService('dashboard')}
                >
                    <Layout size={16} style={{ marginRight: '0.5rem' }} /> Dashboard
                </div>

                <div
                    className={`service-item ${activeService === 'builder' ? 'active' : ''}`}
                    onClick={() => setActiveService('builder')}
                >
                    <PenTool size={16} style={{ marginRight: '0.5rem' }} /> Builder
                </div>

                <div style={{ marginTop: '1rem', marginBottom: '0.5rem', fontSize: '0.75rem', textTransform: 'uppercase', color: '#64748b', fontWeight: 'bold' }}>
                    Services
                </div>

                {services.map(service => (
                    <div
                        key={service.serviceId}
                        className={`service-item ${activeService === service.serviceId ? 'active' : ''}`}
                        onClick={() => setActiveService(service.serviceId)}
                    >
                        {service.label}
                    </div>
                ))}
            </aside>

            <main className="main-content">
                {activeService === 'dashboard' ? (
                    <Dashboard services={services} />
                ) : activeService === 'builder' ? (
                    <ArchitectureBuilder services={services} />
                ) : (
                    <Suspense fallback={<div>Loading calculator...</div>}>
                        {CalculatorComponent ? (
                            <CalculatorComponent serviceId={activeService} />
                        ) : (
                            <div className="card">
                                <h2>Component Not Found</h2>
                                <p>The calculator for {activeService} could not be loaded.</p>
                            </div>
                        )}
                    </Suspense>
                )}
            </main>
        </div>
    )
}

function Dashboard({ services }) {
    return (
        <div>
            <div className="header">
                <h1>Dashboard</h1>
                <p style={{ color: 'var(--text-secondary)' }}>Overview of your potential cloud architecture.</p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '1.5rem' }}>
                {services.map(s => (
                    <div key={s.serviceId} className="card">
                        <h3>{s.label}</h3>
                        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                            Configure and estimate costs for {s.label}.
                        </p>
                    </div>
                ))}
            </div>
        </div>
    )
}

export default App
