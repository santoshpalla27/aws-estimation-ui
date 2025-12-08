<button onClick={() => setSelectedNode(null)} className="text-gray-500 hover:text-gray-700">✕</button>
                    </div >

                    <div className="mb-4">
                        <div className="text-sm font-semibold text-gray-500">Service</div>
                        <div className="text-lg text-blue-600 dark:text-blue-400 font-bold">{selectedNode.data.label}</div>
                    </div>

                    <div className="mb-4">
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Select Pricing Option</label>
                        {configLoading ? (
                            <div className="text-sm text-gray-500">Loading options...</div>
                        ) : (
                            <div className="max-h-60 overflow-y-auto border rounded dark:border-gray-700">
                                {pricingOptions.map((opt, idx) => (
                                    <div
                                        key={idx}
                                        onClick={() => setSelectedPrice(opt)}
                                        className={`p-2 text-sm cursor-pointer border-b dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 ${selectedPrice === opt ? 'bg-blue-100 dark:bg-blue-900' : ''}`}
                                    >
                                        <div className="font-semibold dark:text-gray-200">${opt.price} /{opt.unit}</div>
                                        <div className="text-xs text-gray-500">{opt.description}</div>
                                    </div>
                                ))}
                            </div>
                        )}
                        <p className="text-xs text-gray-400 mt-1">Showing top 50 results. Use the full calculator for advanced filtering.</p>
                    </div>

                    <button
                        onClick={applyConfiguration}
                        disabled={!selectedPrice}
                        className={`w-full py-2 rounded font-bold ${selectedPrice ? 'bg-green-600 text-white hover:bg-green-700' : 'bg-gray-300 text-gray-500 cursor-not-allowed'}`}
                    >
                        Apply Configuration
                    </button>
                </div >
            )}
        </div >
    );
};

export default () => (
    <ReactFlowProvider>
        <ArchitectureBuilder />
    </ReactFlowProvider>
);
