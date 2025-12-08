import React, { useState, useEffect } from 'react';

const GenericCalculator = ({ serviceId, onAddEstimate }) => {
    const [region, setRegion] = useState('us-east-1');
    const [metadata, setMetadata] = useState({ attributes: [] });
    const [filters, setFilters] = useState({});
    const [pricingOptions, setPricingOptions] = useState([]);
    const [selectedPrice, setSelectedPrice] = useState(null);
    const [quantity, setQuantity] = useState(1);
    const [loading, setLoading] = useState(false);

    // Load Metadata (Attributes available for this service)
    useEffect(() => {
        // Reset
        setFilters({});
        setPricingOptions([]);
        setSelectedPrice(null);

        fetch(`http://localhost:8000/api/services/${serviceId}/metadata`)
            .then(res => res.json())
            .then(data => {
                setMetadata(data);
            })
            .catch(e => console.error(e));
    }, [serviceId]);

    // Load Pricing based on filters
    useEffect(() => {
        const params = new URLSearchParams();
        params.append('region', region);
        Object.keys(filters).forEach(key => {
            if (filters[key]) params.append(key, filters[key]);
        });

        setLoading(true);
        fetch(`http://localhost:8000/api/pricing/${serviceId}?${params.toString()}`)
            .then(res => res.json())
            .then(data => {
                setPricingOptions(data);
                setLoading(false);
            })
            .catch(e => {
                console.error(e);
                setLoading(false);
            });
    }, [serviceId, region, filters]);

    const handleFilterChange = (key, value) => {
        setFilters(prev => ({ ...prev, [key]: value }));
    };

    const handleAdd = () => {
        if (selectedPrice) {
            onAddEstimate({
                service: serviceId,
                region,
                details: selectedPrice.description || "Custom Estimate",
                cost: (parseFloat(selectedPrice.price) || 0) * quantity
            });
        }
    };

    return (
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-lg">
            <h2 className="text-xl font-bold mb-4 text-gray-800 dark:text-white capitalize">{serviceId} Estimator</h2>

            {/* Region Selector */}
            <div className="mb-4">
                <label className="block text-gray-700 dark:text-gray-300 mb-2">Region (Global Filter)</label>
                <select value={region} onChange={(e) => setRegion(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:text-white">
                    <option value="us-east-1">US East (N. Virginia)</option>
                    <option value="us-west-2">US West (Oregon)</option>
                    <option value="eu-central-1">Europe (Frankfurt)</option>
                    <option value="ap-south-1">Asia Pacific (Mumbai)</option>
                </select>
            </div>

            {/* Dynamic Filter Inputs */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                {/* Simple text inputs for filters for now - In full version, these would be dropdowns fetched from API */}
                {/* We pick top 3-4 interesting attributes if available, or just render a search box */}
                {metadata.attributes && metadata.attributes.slice(0, 5).map(attr => (
                    <div key={attr}>
                        <label className="block text-gray-700 dark:text-gray-300 mb-1 capitalize">{attr}</label>
                        <input
                            type="text"
                            placeholder={`Filter by ${attr}`}
                            className="w-full p-2 border rounded dark:bg-gray-700 dark:text-white"
                            onChange={(e) => handleFilterChange(attr, e.target.value)}
                        />
                    </div>
                ))}
            </div>

            {/* Results Table */}
            <div className="mb-4 max-h-60 overflow-y-auto border rounded dark:border-gray-700">
                {loading ? <div className="p-4">Loading pricing...</div> : (
                    <table className="min-w-full text-sm">
                        <thead className="bg-gray-50 dark:bg-gray-700">
                            <tr>
                                <th className="px-4 py-2 text-left dark:text-white">Description</th>
                                <th className="px-4 py-2 text-right dark:text-white">Price (USD)</th>
                                <th className="px-4 py-2 text-right dark:text-white">Unit</th>
                                <th className="px-4 py-2"></th>
                            </tr>
                        </thead>
                        <tbody>
                            {pricingOptions.map((opt, idx) => (
                                <tr key={idx} className="border-t dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-900">
                                    <td className="px-4 py-2 dark:text-gray-300">{opt.description || opt.attributes?.group || "N/A"}</td>
                                    <td className="px-4 py-2 text-right dark:text-white">${opt.price || opt.ondemand}</td>
                                    <td className="px-4 py-2 text-right dark:text-gray-300">{opt.unit || "Hr"}</td>
                                    <td className="px-4 py-2 text-right">
                                        <button
                                            onClick={() => setSelectedPrice(opt)}
                                            className={`px-3 py-1 rounded ${selectedPrice === opt ? 'bg-green-500 text-white' : 'bg-gray-200 text-gray-800'}`}
                                        >
                                            Select
                                        </button>
                                    </td>
                                </tr>
                            ))}
                            {pricingOptions.length === 0 && (
                                <tr><td colSpan="4" className="p-4 text-center dark:text-gray-400">No matching pricing found. Try adjusting filters.</td></tr>
                            )}
                        </tbody>
                    </table>
                )}
            </div>

            {/* Calculation */}
            {selectedPrice && (
                <div className="bg-gray-100 dark:bg-gray-900 p-4 rounded mb-4">
                    <h3 className="font-bold dark:text-white mb-2">Estimate Config</h3>
                    <div className="flex items-center gap-4">
                        <div className="flex-1">
                            <label className="block text-gray-600 dark:text-gray-400 text-xs">Quantity / Units</label>
                            <input
                                type="number"
                                value={quantity}
                                onChange={(e) => setQuantity(parseFloat(e.target.value))}
                                className="w-full p-2 border rounded dark:bg-gray-700 dark:text-white"
                            />
                        </div>
                        <div className="text-right">
                            <div className="text-sm text-gray-500">Total</div>
                            <div className="text-xl font-bold dark:text-white">
                                ${((parseFloat(selectedPrice.price) || parseFloat(selectedPrice.ondemand) || 0) * quantity).toFixed(4)}
                            </div>
                        </div>
                    </div>
                </div>
            )}

            <button
                onClick={handleAdd}
                disabled={!selectedPrice}
                className={`w-full py-2 rounded transition ${selectedPrice ? 'bg-blue-600 text-white hover:bg-blue-700' : 'bg-gray-300 cursor-not-allowed'}`}
            >
                Add to Estimate
            </button>
        </div>
    );
};

export default GenericCalculator;
