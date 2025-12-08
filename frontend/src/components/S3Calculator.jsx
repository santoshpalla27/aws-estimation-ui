import React, { useState, useEffect } from 'react';

const S3Calculator = ({ onAddEstimate }) => {
    const [region, setRegion] = useState('us-east-1');
    const [storageClass, setStorageClass] = useState('Standard');
    const [storage, setStorage] = useState(100);
    const [requests, setRequests] = useState(1000); // Tier 1 approx
    const [dataTransfer, setDataTransfer] = useState(0);
    const [estimate, setEstimate] = useState(null);

    useEffect(() => {
        calculate();
    }, [region, storageClass, storage, requests, dataTransfer]);

    const calculate = async () => {
        try {
            const res = await fetch('/api/estimate/s3', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    region,
                    storage_class: storageClass,
                    storage_gb: storage,
                    requests: requests,
                    data_transfer_gb: dataTransfer
                })
            });
            const data = await res.json();
            setEstimate(data);
        } catch (e) {
            console.error("API Error", e);
        }
    };

    const handleAdd = () => {
        if (estimate) {
            onAddEstimate({
                service: 'S3',
                region,
                details: `${storageClass}, ${storage}GB, ${dataTransfer}GB Transfer`,
                cost: estimate.monthly_cost
            });
        }
    };

    return (
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-lg">
            <h2 className="text-xl font-bold mb-4 text-gray-800 dark:text-white">S3 Estimator</h2>

            <div className="mb-4">
                <label className="block text-gray-700 dark:text-gray-300 mb-2">Region</label>
                <select value={region} onChange={(e) => setRegion(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:text-white">
                    <option value="us-east-1">US East (N. Virginia)</option>
                    <option value="us-west-2">US West (Oregon)</option>
                    <option value="eu-central-1">Europe (Frankfurt)</option>
                </select>
            </div>

            <div className="mb-4">
                <label className="block text-gray-700 dark:text-gray-300 mb-2">Storage Class</label>
                <select value={storageClass} onChange={(e) => setStorageClass(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:text-white">
                    <option value="Standard">S3 Standard</option>
                    <option value="Intelligent-Tiering">Intelligent-Tiering</option>
                    <option value="Standard-IA">Standard-IA</option>
                    <option value="One Zone-IA">One Zone-IA</option>
                    <option value="Glacier">Glacier Instant Retrieval</option>
                    <option value="Deep Archive">Glacier Deep Archive</option>
                </select>
            </div>

            <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                    <label className="block text-gray-700 dark:text-gray-300 mb-2">Storage (GB)</label>
                    <input
                        type="number"
                        min="0"
                        value={storage}
                        onChange={(e) => setStorage(parseFloat(e.target.value))}
                        className="w-full p-2 border rounded dark:bg-gray-700 dark:text-white"
                    />
                </div>
                <div>
                    <label className="block text-gray-700 dark:text-gray-300 mb-2">Monthly Requests</label>
                    <input
                        type="number"
                        min="0"
                        value={requests}
                        onChange={(e) => setRequests(parseFloat(e.target.value))}
                        className="w-full p-2 border rounded dark:bg-gray-700 dark:text-white"
                    />
                </div>
                <div className="col-span-2">
                    <label className="block text-gray-700 dark:text-gray-300 mb-2">Data Transfer Out (GB)</label>
                    <input
                        type="number"
                        min="0"
                        value={dataTransfer}
                        onChange={(e) => setDataTransfer(parseFloat(e.target.value))}
                        className="w-full p-2 border rounded dark:bg-gray-700 dark:text-white"
                    />
                </div>
            </div>

            <div className="bg-gray-100 dark:bg-gray-900 p-4 rounded mb-4">
                <h3 className="text-sm font-bold text-gray-500 mb-2 uppercase">Cost Breakdown</h3>

                <div className="flex justify-between items-center mb-1 text-sm">
                    <span className="dark:text-gray-300">Storage</span>
                    <span className="font-mono dark:text-white">${estimate?.details?.storage || '0.00'}</span>
                </div>
                <div className="flex justify-between items-center mb-1 text-sm">
                    <span className="dark:text-gray-300">Requests</span>
                    <span className="font-mono dark:text-white">${estimate?.details?.requests || '0.00'}</span>
                </div>
                <div className="flex justify-between items-center mb-2 text-sm">
                    <span className="dark:text-gray-300">Data Transfer</span>
                    <span className="font-mono dark:text-white">${estimate?.details?.data_transfer || '0.00'}</span>
                </div>

                <div className="border-t dark:border-gray-700 pt-2 flex justify-between items-center font-bold text-lg dark:text-white">
                    <span>Total Estimated:</span>
                    <span>${estimate?.monthly_cost || '0.00'} / mo</span>
                </div>
            </div>

            <button
                onClick={handleAdd}
                className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 transition"
            >
                Add to Estimate
            </button>
        </div>
    );
};

export default S3Calculator;
