import React from 'react';

const Dashboard = ({ totalCost, items }) => {

    const handleExport = async (format) => {
        if (!items || items.length === 0) return;

        try {
            const res = await fetch(`/api/export/${format}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ items })
            });

            if (res.ok) {
                const blob = await res.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `cost_report.${format}`;
                document.body.appendChild(a);
                a.click();
                a.remove();
            }
        } catch (e) {
            console.error("Export failed", e);
        }
    };

    return (
        <div className="p-6">
            <h2 className="text-3xl font-bold mb-6 text-gray-800 dark:text-white">Cost Overview</h2>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow border-l-4 border-blue-500">
                    <h3 className="text-gray-500 text-sm font-bold uppercase mb-2">Total Monthly Estimate</h3>
                    <p className="text-4xl font-bold text-gray-900 dark:text-white">${totalCost.toFixed(2)}</p>
                </div>
                <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow border-l-4 border-green-500">
                    <h3 className="text-gray-500 text-sm font-bold uppercase mb-2">Service Count</h3>
                    <p className="text-4xl font-bold text-gray-900 dark:text-white">{items.length}</p>
                </div>
                <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow flex flex-col justify-center items-start gap-2">
                    <button
                        onClick={() => handleExport('json')}
                        disabled={items.length === 0}
                        className="w-full bg-gray-100 hover:bg-gray-200 text-gray-800 font-bold py-2 px-4 rounded inline-flex items-center justify-center disabled:opacity-50"
                    >
                        <span>Export JSON</span>
                    </button>
                    <button
                        onClick={() => handleExport('pdf')}
                        disabled={items.length === 0}
                        className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded inline-flex items-center justify-center disabled:opacity-50"
                    >
                        <span>Export PDF Report</span>
                    </button>
                </div>
            </div>

            <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
                <table className="min-w-full">
                    <thead className="bg-gray-100 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
                        <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Service</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Region</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Details</th>
                            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Cost</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                        {items.map((item, idx) => (
                            <tr key={idx} className="hover:bg-gray-50 dark:hover:bg-gray-750">
                                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">{item.service}</td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-300">{item.region}</td>
                                <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-300">{item.details}</td>
                                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-bold text-gray-900 dark:text-white">${item.cost.toFixed(2)}</td>
                            </tr>
                        ))}
                        {items.length === 0 && (
                            <tr>
                                <td colSpan="4" className="px-6 py-12 text-center text-gray-500">
                                    No estimates added yet. Select a service to begin.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default Dashboard;
