import React, { useState, useEffect } from 'react';

// Sub-component for individual attribute dropdowns
const AttributeSelect = ({ service, attribute, region, value, onChange }) => {
    const [options, setOptions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [disabled, setDisabled] = useState(false);

    useEffect(() => {
        let active = true;
        setLoading(true);
        setDisabled(false);

        // Fetch unique values for this attribute, filtered by current region
        const params = new URLSearchParams({ region });

        fetch(`/api/pricing/${service}/attributes/${attribute}?${params.toString()}`)
            .then(res => {
                if (!res.ok) throw new Error("Failed to load");
                return res.json();
            })
            .then(data => {
                if (active) {
                    setOptions(data);
                    setLoading(false);
                    // Disable if no options (except if loading error)
                    if (data.length === 0) setDisabled(true);
                }
            })
            .catch(e => {
                console.error(e);
                if (active) {
                    setLoading(false);
                    setDisabled(true);
                }
            });

        return () => { active = false; };
    }, [service, attribute, region]);

    if (loading) {
        return (
            <div className="animate-pulse">
                <label className="block text-gray-700 dark:text-gray-300 mb-1 text-xs capitalize">{attribute}</label>
                <div className="h-10 bg-gray-200 dark:bg-gray-700 rounded"></div>
            </div>
        );
    }

    if (disabled && !value) return null; // Hide useless filters if empty

    return (
        <div>
            <label className="block text-gray-700 dark:text-gray-300 mb-1 text-xs capitalize">{attribute}</label>
            <select
                value={value || ""}
                onChange={(e) => onChange(e.target.value)}
                className="w-full p-2 border rounded dark:bg-gray-700 dark:text-white text-sm"
            >
                <option value="">Any</option>
                {options.map(opt => (
                    <option key={opt} value={opt}>{opt}</option>
                ))}
            </select>
        </div>
    );
};

const GenericCalculator = ({ serviceId, onAddEstimate }) => {
    const [region, setRegion] = useState('us-east-1');
    const [metadata, setMetadata] = useState({ attributes: [] });
    const [filters, setFilters] = useState({});
    const [pricingOptions, setPricingOptions] = useState([]);
    const [selectedPrice, setSelectedPrice] = useState(null);
    const [quantity, setQuantity] = useState(1);
    const [loadingItems, setLoadingItems] = useState(false);

    // Pagination
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);

    // Load Metadata
    useEffect(() => {
        setFilters({});
        setPricingOptions([]);
        setSelectedPrice(null);
        setPage(1);

        fetch(`/api/services/${serviceId}/metadata`)
            .then(res => res.json())
            .then(setMetadata)
            .catch(console.error);
    }, [serviceId]);

    // Reset pagination when filters change
    useEffect(() => {
        setPage(1);
    }, [region, filters]);

    // Load Pricing with Pagination
    useEffect(() => {
        const params = new URLSearchParams();
        params.append('region', region);
        params.append('page', page);
        params.append('page_size', 20);

        Object.keys(filters).forEach(key => {
            if (filters[key]) params.append(key, filters[key]);
        });

        setLoadingItems(true);
        fetch(`/api/pricing/${serviceId}?${params.toString()}`)
            .then(res => res.json())
            .then(data => {
                setPricingOptions(data.items || []);
                setTotalPages(data.total_pages || 1);
                setLoadingItems(false);
            })
            .catch(e => {
                console.error(e);
                setLoadingItems(false);
            });
    }, [serviceId, region, filters, page]);

    const handleFilterChange = (key, value) => {
        setFilters(prev => {
            const next = { ...prev, [key]: value };
            if (!value) delete next[key];
            return next;
        });
    };

    const handleClearFilters = () => {
        setFilters({});
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
            <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-bold text-gray-800 dark:text-white capitalize">{serviceId} Estimator</h2>
                <button
                    onClick={handleClearFilters}
                    className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
                >
                    Clear Filters
                </button>
            </div>

            {/* Global Region Filter */}
            <div className="mb-6 p-4 bg-gray-50 dark:bg-gray-900 rounded border dark:border-gray-700">
                <label className="block text-gray-700 dark:text-gray-300 mb-2 font-semibold">Step 1: Select Region</label>
                <select value={region} onChange={(e) => setRegion(e.target.value)} className="w-full p-2 border rounded dark:bg-gray-700 dark:text-white">
                    <option value="us-east-1">US East (N. Virginia)</option>
                    <option value="us-west-2">US West (Oregon)</option>
                    <option value="eu-central-1">Europe (Frankfurt)</option>
                    <option value="ap-south-1">Asia Pacific (Mumbai)</option>
                </select>
            </div>

            {/* Dynamic Attribute Filters */}
            <div className="mb-6">
                <label className="block text-gray-700 dark:text-gray-300 mb-3 font-semibold">Step 2: Filter Options</label>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                    {metadata.attributes && metadata.attributes.slice(0, 12).map(attr => (
                        <AttributeSelect
                            key={attr}
                            service={serviceId}
                            attribute={attr}
                            region={region}
                            value={filters[attr]}
                            onChange={(val) => handleFilterChange(attr, val)}
                        />
                    ))}
                </div>
            </div>

            {/* Results */}
            <div className="mb-4">
                <h3 className="font-semibold mb-2 dark:text-white">Available Pricing</h3>
                <div className="border rounded dark:border-gray-700">
                    {loadingItems ? (
                        <div className="p-8 text-center text-gray-500">Loading pricing options...</div>
                    ) : (
                        <>
                            <div className="max-h-96 overflow-y-auto">
                                <table className="min-w-full text-sm">
                                    <thead className="bg-gray-100 dark:bg-gray-900 sticky top-0">
                                        <tr>
                                            <th className="px-4 py-2 text-left dark:text-white">Description</th>
                                            <th className="px-4 py-2 text-right dark:text-white">Price</th>
                                            <th className="px-4 py-2"></th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {pricingOptions.map((opt, idx) => (
                                            <tr
                                                key={idx}
                                                className={`border-t dark:border-gray-700 cursor-pointer ${selectedPrice === opt ? 'bg-blue-50 dark:bg-blue-900' : 'hover:bg-gray-50 dark:hover:bg-gray-800'}`}
                                                onClick={() => setSelectedPrice(opt)}
                                            >
                                                <td className="px-4 py-3 dark:text-gray-300">
                                                    <div className="font-medium">{opt.description || "N/A"}</div>
                                                    <div className="text-xs text-gray-500">
                                                        {Object.entries(opt.attributes || {}).slice(0, 3).map(([k, v]) => `${k}: ${v}`).join(', ')}
                                                    </div>
                                                </td>
                                                <td className="px-4 py-3 text-right dark:text-white">
                                                    ${opt.price} <span className="text-xs text-gray-500">/{opt.unit}</span>
                                                </td>
                                                <td className="px-4 py-3 text-right">
                                                    {selectedPrice === opt && <span className="text-blue-600">Selected</span>}
                                                </td>
                                            </tr>
                                        ))}
                                        {pricingOptions.length === 0 && (
                                            <tr><td colSpan="3" className="p-8 text-center dark:text-gray-400">No options found. Try clearing filters.</td></tr>
                                        )}
                                    </tbody>
                                </table>
                            </div>

                            {/* Pagination Controls */}
                            <div className="bg-gray-50 dark:bg-gray-800 p-2 border-t dark:border-gray-700 flex justify-between items-center">
                                <button
                                    onClick={() => setPage(p => Math.max(1, p - 1))}
                                    disabled={page === 1}
                                    className="px-3 py-1 bg-white dark:bg-gray-700 border rounded text-sm disabled:opacity-50"
                                >
                                    Previous
                                </button>
                                <span className="text-sm dark:text-gray-300">
                                    Page {page} of {totalPages}
                                </span>
                                <button
                                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                                    disabled={page >= totalPages}
                                    className="px-3 py-1 bg-white dark:bg-gray-700 border rounded text-sm disabled:opacity-50"
                                >
                                    Next
                                </button>
                            </div>
                        </>
                    )}
                </div>
            </div>

            {/* Calculation */}
            <div className="bg-gray-100 dark:bg-gray-900 p-4 rounded mb-4 flex items-center gap-4">
                <div className="flex-1">
                    <label className="block text-gray-600 dark:text-gray-400 text-xs uppercase font-bold">Quantity</label>
                    <input
                        type="number"
                        min="1"
                        value={quantity}
                        onChange={(e) => setQuantity(parseFloat(e.target.value) || 0)}
                        className="w-24 p-2 border rounded dark:bg-gray-700 dark:text-white mt-1"
                    />
                </div>
                <div className="text-right">
                    <div className="text-sm text-gray-500">Total Monthly Cost</div>
                    <div className="text-2xl font-bold dark:text-white">
                        ${selectedPrice ? (parseFloat(selectedPrice.price) * quantity).toFixed(2) : '0.00'}
                    </div>
                </div>
            </div>

            <button
                onClick={handleAdd}
                disabled={!selectedPrice}
                className={`w-full py-3 rounded font-bold shadow transition ${selectedPrice ? 'bg-blue-600 text-white hover:bg-blue-700' : 'bg-gray-300 text-gray-500 cursor-not-allowed'}`}
            >
                ADD TO ESTIMATE
            </button>
        </div>
    );
};

export default GenericCalculator;
