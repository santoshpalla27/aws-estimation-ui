import React, { useState, useEffect } from 'react';
import Dashboard from './components/Dashboard';
import EC2Calculator from './components/EC2Calculator';
import S3Calculator from './components/S3Calculator';
import GenericCalculator from './components/GenericCalculator';

function App() {
    const [activeTab, setActiveTab] = useState('dashboard');
    const [estimates, setEstimates] = useState([]);
    const [services, setServices] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch('http://localhost:8000/api/services')
            .then(res => res.json())
            .then(data => {
                setServices(data);
                setLoading(false);
            })
            .catch(err => {
                console.error("Failed to fetch services", err);
                setLoading(false);
            });
    }, []);

    const totalCost = estimates.reduce((acc, item) => acc + item.cost, 0);

    const addEstimate = (item) => {
        setEstimates([...estimates, item]);
        setActiveTab('dashboard');
    };

    const renderContent = () => {
        if (activeTab === 'dashboard') {
            return <Dashboard totalCost={totalCost} items={estimates} />;
        }
        if (activeTab === 'EC2' || activeTab === 'AmazonEC2') {
            return <div className="p-6"><EC2Calculator onAddEstimate={addEstimate} /></div>;
        }
        if (activeTab === 'S3' || activeTab === 'AmazonS3') {
            return <div className="p-6"><S3Calculator onAddEstimate={addEstimate} /></div>;
        }

        // Generic Handler for all other services
        return (
            <div className="p-6">
                <GenericCalculator
                    serviceId={activeTab}
                    onAddEstimate={addEstimate}
                />
            </div>
        );
    };

    return (
        <div className="flex h-screen bg-gray-100 dark:bg-gray-900">
            {/* Sidebar */}
            <div className="w-64 bg-white dark:bg-gray-800 shadow-lg flex flex-col">
                <div className="p-6">
                    <h1 className="text-2xl font-bold text-blue-600 dark:text-blue-400">AWS Estimator</h1>
                </div>
                <nav className="mt-4 flex-1 overflow-y-auto">
                    <button
                        onClick={() => setActiveTab('dashboard')}
                        className={`w-full text-left px-6 py-3 hover:bg-gray-50 dark:hover:bg-gray-700 ${activeTab === 'dashboard' ? 'bg-blue-50 dark:bg-gray-700 border-r-4 border-blue-500' : ''}`}
                    >
                        <span className="text-gray-700 dark:text-gray-200 font-bold">Dashboard</span>
                    </button>

                    <div className="px-6 py-2 text-xs font-semibold text-gray-500 uppercase">Services</div>

                    {loading ? (
                        <div className="px-6 py-2 text-gray-400">Loading...</div>
                    ) : (
                        services.map(svc => (
                            <button
                                key={svc.id}
                                onClick={() => setActiveTab(svc.id)}
                                className={`w-full text-left px-6 py-2 hover:bg-gray-50 dark:hover:bg-gray-700 ${activeTab === svc.id ? 'bg-blue-50 dark:bg-gray-700 border-r-4 border-blue-500' : ''}`}
                            >
                                <span className="text-gray-700 dark:text-gray-200 truncate block">{svc.name}</span>
                            </button>
                        ))
                    )}
                </nav>
            </div>

            {/* Main Content */}
            <div className="flex-1 overflow-auto">
                {renderContent()}
            </div>
        </div>
    );
}

export default App;
