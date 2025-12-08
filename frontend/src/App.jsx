import React, { useState } from 'react';
import Dashboard from './components/Dashboard';
import EC2Calculator from './components/EC2Calculator';
import S3Calculator from './components/S3Calculator';

function App() {
    const [activeTab, setActiveTab] = useState('dashboard');
    const [estimates, setEstimates] = useState([]);

    const totalCost = estimates.reduce((acc, item) => acc + item.cost, 0);

    const addEstimate = (item) => {
        setEstimates([...estimates, item]);
        setActiveTab('dashboard');
    };

    return (
        <div className="flex h-screen bg-gray-100 dark:bg-gray-900">
            {/* Sidebar */}
            <div className="w-64 bg-white dark:bg-gray-800 shadow-lg">
                <div className="p-6">
                    <h1 className="text-2xl font-bold text-blue-600 dark:text-blue-400">AWS Estimator</h1>
                </div>
                <nav className="mt-4">
                    <button
                        onClick={() => setActiveTab('dashboard')}
                        className={`w-full text-left px-6 py-3 hover:bg-gray-50 dark:hover:bg-gray-700 ${activeTab === 'dashboard' ? 'bg-blue-50 dark:bg-gray-700 border-r-4 border-blue-500' : ''}`}
                    >
                        <span className="text-gray-700 dark:text-gray-200">Dashboard</span>
                    </button>
                    <button
                        onClick={() => setActiveTab('ec2')}
                        className={`w-full text-left px-6 py-3 hover:bg-gray-50 dark:hover:bg-gray-700 ${activeTab === 'ec2' ? 'bg-blue-50 dark:bg-gray-700 border-r-4 border-blue-500' : ''}`}
                    >
                        <span className="text-gray-700 dark:text-gray-200">EC2 Calculator</span>
                    </button>
                    <button
                        onClick={() => setActiveTab('s3')}
                        className={`w-full text-left px-6 py-3 hover:bg-gray-50 dark:hover:bg-gray-700 ${activeTab === 's3' ? 'bg-blue-50 dark:bg-gray-700 border-r-4 border-blue-500' : ''}`}
                    >
                        <span className="text-gray-700 dark:text-gray-200">S3 Calculator</span>
                    </button>
                </nav>
            </div>

            {/* Main Content */}
            <div className="flex-1 overflow-auto">
                {activeTab === 'dashboard' && <Dashboard totalCost={totalCost} items={estimates} />}
                {activeTab === 'ec2' && (
                    <div className="p-6">
                        <EC2Calculator onAddEstimate={addEstimate} />
                    </div>
                )}
                {activeTab === 's3' && (
                    <div className="p-6">
                        <S3Calculator onAddEstimate={addEstimate} />
                    </div>
                )}
            </div>
        </div>
    );
}

export default App;
