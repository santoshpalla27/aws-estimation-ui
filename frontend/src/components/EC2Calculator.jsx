import React, { useState, useEffect } from 'react';

const EC2Calculator = ({ onAddEstimate }) => {
    const [region, setRegion] = useState('us-east-1');
    const [instanceType, setInstanceType] = useState('t3.micro');
    const [hours, setHours] = useState(730);
    const [storage, setStorage] = useState(30);
    const [volumeType, setVolumeType] = useState('gp3');
    const [term, setTerm] = useState('ondemand');
    const [estimate, setEstimate] = useState(null);

    // Mock loading data
    useEffect(() => {
        calculate();
    }, [region, instanceType, hours, storage, volumeType, term]);

    const calculate = async () => {
        try {
            const res = await fetch('/api/estimate/ec2', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    region,
                    instance_type: instanceType,
                    hours_per_month: hours,
                    term: term,
                    storage_gb: storage,
                    ebs_volume_type: volumeType
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
                service: 'EC2',
                region,
                details: `${instanceType}, ${storage}GB ${volumeType}`,
                cost: estimate.monthly_cost
            });
        }
    };

    return (
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-lg">
            <h2 className="text-xl font-bold mb-4 text-gray-800 dark:text-white">EC2 Estimator</h2>

            <div className="mb-4">
                <label className="block text-gray-700 dark:text-gray-300 mb-2">Region</label>
                <select value={region} onChange={(e) => setRegion(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:text-white">
                    <option value="us-east-1">US East (N. Virginia)</option>
                    <option value="us-west-2">US West (Oregon)</option>
                    <option value="eu-central-1">Europe (Frankfurt)</option>
                    <option value="ap-south-1">Asia Pacific (Mumbai)</option>
                </select>
            </div>

            <div className="mb-4">
                <label className="block text-gray-700 dark:text-gray-300 mb-2">Pricing Term</label>
                <select value={term} onChange={(e) => setTerm(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:text-white">
                    <option value="ondemand">On Demand</option>
                    <option value="reserved_1yr">Reserved (1 Year)</option>
                    <option value="spot">Spot Instance</option>
                </select>
            </div>


            <div className="mb-4">
                <label className="block text-gray-700 dark:text-gray-300 mb-2">Instance Type</label>
                <input
                    type="text"
                    value={instanceType}
                    onChange={(e) => setInstanceType(e.target.value)}
                    className="w-full p-2 border rounded dark:bg-gray-700 dark:text-white"
                    placeholder="e.g. t3.micro"
                />
            </div>

            <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                    <label className="block text-gray-700 dark:text-gray-300 mb-2">Hours / Month</label>
                    <input
                        type="number"
                        value={hours}
                        onChange={(e) => setHours(e.target.value)}
                        className="w-full p-2 border rounded dark:bg-gray-700 dark:text-white"
                    />
                </div>
                <div>
                    <label className="block text-gray-700 dark:text-gray-300 mb-2">Storage (GB)</label>
                    <input
                        type="number"
                        value={storage}
                        onChange={(e) => setStorage(e.target.value)}
                        className="w-full p-2 border rounded dark:bg-gray-700 dark:text-white"
                    />
                </div>
            </div>

            <div className="mb-4">
                <label className="block text-gray-700 dark:text-gray-300 mb-2">EBS Volume Type</label>
                <select value={volumeType} onChange={(e) => setVolumeType(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:text-white">
                    <option value="gp3">General Purpose SSD (gp3)</option>
                    <option value="gp2">General Purpose SSD (gp2)</option>
                    <option value="io1">Provisioned IOPS SSD (io1)</option>
                    <option value="io2">Provisioned IOPS SSD (io2)</option>
                    <option value="st1">Throughput Optimized HDD (st1)</option>
                    <option value="sc1">Cold HDD (sc1)</option>
                    <option value="standard">Magnetic (standard)</option>
                </select>
            </div>

            <div className="bg-gray-100 dark:bg-gray-900 p-4 rounded mb-4">
                <div className="flex justify-between items-center mb-2">
                    <span className="text-gray-600 dark:text-gray-400">Compute:</span>
                    <span className="font-mono dark:text-white">${estimate?.details?.compute || '0.00'}</span>
                </div>
                <div className="flex justify-between items-center mb-2">
                    <span className="text-gray-600 dark:text-gray-400">Storage ({estimate?.details?.storage_type || volumeType}):</span>
                    <span className="font-mono dark:text-white">${estimate?.details?.storage || '0.00'}</span>
                </div>
                <div className="border-t pt-2 mt-2 flex justify-between items-center font-bold text-lg dark:text-white">
                    <span>Total:</span>
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

export default EC2Calculator;
