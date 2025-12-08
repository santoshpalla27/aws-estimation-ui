import React, { useState, useRef, useCallback, useEffect } from 'react';
import ReactFlow, {
    ReactFlowProvider,
    addEdge,
    useNodesState,
    useEdgesState,
    Controls,
    Background,
    MiniMap,
    Panel
} from 'reactflow';
import 'reactflow/dist/style.css';

import ServiceNode from './ServiceNode';

const nodeTypes = {
    serviceNode: ServiceNode,
};

const SERVICES_PALETTE = [
    { id: 'AmazonEC2', label: 'EC2 Instance', icon: '🖥️' },
    { id: 'AmazonS3', label: 'S3 Bucket', icon: '🪣' },
    { id: 'AmazonRDS', label: 'RDS Database', icon: '🗄️' },
    { id: 'AmazonLambda', label: 'Lambda Function', icon: '⚡' },
    { id: 'AmazonVPC', label: 'VPC', icon: '🌐' },
    { id: 'AWSELB', label: 'Load Balancer', icon: '⚖️' }
];

let id = 0;
const getId = () => `node_${id++}`;

const ArchitectureBuilder = () => {
    const reactFlowWrapper = useRef(null);
    const [nodes, setNodes, onNodesChange] = useNodesState([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState([]);
    const [reactFlowInstance, setReactFlowInstance] = useState(null);
    const [selectedNode, setSelectedNode] = useState(null);
    const [configLoading, setConfigLoading] = useState(false);
    const [pricingOptions, setPricingOptions] = useState([]);
    const [selectedPrice, setSelectedPrice] = useState(null);

    // Total Cost Calculation
    const totalCost = nodes.reduce((acc, node) => acc + (node.data.cost || 0), 0);

    const onConnect = useCallback((params) => setEdges((eds) => addEdge(params, eds)), [setEdges]);

    const onDragOver = useCallback((event) => {
        event.preventDefault();
        event.dataTransfer.dropEffect = 'move';
    }, []);

    const onDrop = useCallback(
        (event) => {
            event.preventDefault();

            const type = event.dataTransfer.getData('application/reactflow');
            const serviceId = event.dataTransfer.getData('serviceId');
            const icon = event.dataTransfer.getData('icon');
            const label = event.dataTransfer.getData('label');

            if (typeof type === 'undefined' || !type) {
                return;
            }

            const position = reactFlowInstance.screenToFlowPosition({
                x: event.clientX,
                y: event.clientY,
            });

            const newNode = {
                id: getId(),
                type: 'serviceNode',
                position,
                data: { label, serviceId, icon, cost: 0, details: 'Configure me' },
            };

            setNodes((nds) => nds.concat(newNode));
        },
        [reactFlowInstance, setNodes]
    );

    // Node Selection Handler
    const onNodeClick = (event, node) => {
        setSelectedNode(node);
        // Reset config state
        setPricingOptions([]);
        setSelectedPrice(null);
        fetchPricing(node.data.serviceId);
    };

    const fetchPricing = async (serviceId) => {
        setConfigLoading(true);
        try {
            // Fetch default/initial options. Ideally we support filtering here.
            // For MVP builder, we just fetch a page of options.
            const res = await fetch(`/api/pricing/${serviceId}?page=1&page_size=50`);
            const data = await res.json();
            setPricingOptions(data.items || []);
        } catch (e) {
            console.error(e);
        } finally {
            setConfigLoading(false);
        }
    };

    const applyConfiguration = () => {
        if (!selectedNode || !selectedPrice) return;

        setNodes((nds) =>
            nds.map((node) => {
                if (node.id === selectedNode.id) {
                    return {
                        ...node,
                        data: {
                            ...node.data,
                            cost: parseFloat(selectedPrice.price) || 0,
                            details: selectedPrice.description,
                            configuration: selectedPrice
                        },
                    };
                }
                return node;
            })
        );
        setSelectedNode(null); // Deselect after apply
    };

    const handleExport = () => {
        const exportData = {
            nodes,
            edges,
            totalCost,
            generatedAt: new Date().toISOString()
        };
        const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'architecture_cost.json';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    };

    return (
        <div className="flex h-full w-full">
            {/* Sidebar Palette */}
            <div className="w-16 md:w-48 bg-gray-100 dark:bg-gray-800 border-r dark:border-gray-700 flex flex-col p-2 overflow-y-auto">
                <div className="text-xs font-bold text-gray-500 mb-2 uppercase hidden md:block">Services</div>
                {SERVICES_PALETTE.map((srv) => (
                    <div
                        key={srv.id}
                        className="mb-2 p-2 bg-white dark:bg-gray-700 rounded shadow cursor-grab border dark:border-gray-600 hover:bg-blue-50 dark:hover:bg-gray-600 flex flex-col items-center justify-center md:flex-row md:justify-start"
                        onDragStart={(event) => {
                            event.dataTransfer.setData('application/reactflow', 'serviceNode');
                            event.dataTransfer.setData('serviceId', srv.id);
                            event.dataTransfer.setData('icon', srv.icon);
                            event.dataTransfer.setData('label', srv.label);
                            event.dataTransfer.effectAllowed = 'move';
                        }}
                        draggable
                    >
                        <span className="text-2xl mr-0 md:mr-2">{srv.icon}</span>
                        <span className="text-sm font-medium hidden md:block dark:text-gray-200">{srv.label}</span>
                    </div>
                ))}
            </div>

            {/* Main Canvas */}
            <div className="flex-1 h-full relative" ref={reactFlowWrapper}>
                <ReactFlow
                    nodes={nodes}
                    edges={edges}
                    onNodesChange={onNodesChange}
                    onEdgesChange={onEdgesChange}
                    onConnect={onConnect}
                    onInit={setReactFlowInstance}
                    onDrop={onDrop}
                    onDragOver={onDragOver}
                    onNodeClick={onNodeClick}
                    nodeTypes={nodeTypes}
                    fitView
                >
                    <Controls />
                    <MiniMap />
                    <Background gap={12} size={1} />

                    <Panel position="top-right" className="bg-white dark:bg-gray-800 p-4 rounded shadow-lg border dark:border-gray-700 flex flex-col gap-2">
                        <div className="text-xl font-bold text-gray-800 dark:text-white">
                            Total: ${totalCost.toFixed(2)}/mo
                        </div>
                        <button onClick={handleExport} className="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700">
                            Export JSON
                        </button>
                    </Panel>
                </ReactFlow>
            </div>

            {/* Properties Panel (Right) */}
            {selectedNode && (
                <div className="w-80 bg-white dark:bg-gray-800 border-l dark:border-gray-700 p-4 overflow-y-auto absolute right-0 top-0 bottom-0 shadow-xl z-10 transition-transform">
                    <div className="flex justify-between items-center mb-4">
                        <h2 className="font-bold text-lg dark:text-white">Configure Node</h2>
                        <button onClick={() => setSelectedNode(null)} className="text-gray-500 hover:text-gray-700">✕</button>
                    </div>

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
                </div>
            )}
        </div>
    );
};

export default () => (
    <ReactFlowProvider>
        <ArchitectureBuilder />
    </ReactFlowProvider>
);
