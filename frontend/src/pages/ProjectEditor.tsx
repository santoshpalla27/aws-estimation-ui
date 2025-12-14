import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import ReactFlow, {
    Background,
    Controls,
    MiniMap,
    Node,
    Connection,
    addEdge,
    useNodesState,
    useEdgesState,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { projectsApi, estimatesApi, servicesApi, ServiceMetadata } from '@/lib/api'
import { useProjectStore } from '@/store/projectStore'
import { ServiceNode } from './ServiceNode'
import { ServiceCatalog } from './ServiceCatalog'
import { EstimateSummary } from './EstimateSummary'
import { ServiceConfigDialog } from '@/components/ServiceConfigDialog'
import { generateId } from '@/lib/utils'
import { Calculator } from 'lucide-react'

const nodeTypes = {
    service: ServiceNode,
}

export function ProjectEditor() {
    const { projectId } = useParams<{ projectId: string }>()
    const { nodes: storeNodes, edges: storeEdges, setProjectId, estimate, setEstimate, setIsCalculating } = useProjectStore()

    const [nodes, setNodes, onNodesChange] = useNodesState([])
    const [edges, setEdges, onEdgesChange] = useEdgesState([])
    const [showCatalog] = useState(true)
    const [configDialogOpen, setConfigDialogOpen] = useState(false)
    const [selectedNode, setSelectedNode] = useState<Node | null>(null)

    // Load project
    const { data: project } = useQuery({
        queryKey: ['project', projectId],
        queryFn: async () => {
            const response = await projectsApi.get(projectId!)
            return response.data
        },
        enabled: !!projectId,
    })

    // Load services
    const { data: services } = useQuery({
        queryKey: ['services'],
        queryFn: async () => {
            const response = await servicesApi.list()
            return response.data
        },
    })

    // Calculate estimate mutation
    const calculateMutation = useMutation({
        mutationFn: async () => {
            setIsCalculating(true)
            const response = await estimatesApi.create(projectId!, {
                services: storeNodes.map((node) => ({
                    id: node.id,
                    service_type: node.data.service_type,
                    config: node.data.config || {},
                    region: 'us-east-1',
                    metadata: {},
                })),
                dependencies: storeEdges.map((edge) => ({
                    source: edge.source,
                    target: edge.target,
                    type: 'dependency',
                    reason: 'User defined',
                    metadata: {},
                })),
            })
            return response.data
        },
        onSuccess: (data) => {
            setEstimate(data)
            setIsCalculating(false)
        },
        onError: (error) => {
            console.error('Failed to calculate estimate:', error)
            setIsCalculating(false)
        },
    })

    useEffect(() => {
        if (projectId) {
            setProjectId(projectId)
        }
    }, [projectId, setProjectId])

    const onConnect = (connection: Connection) => {
        setEdges((eds) => addEdge(connection, eds))
    }

    const onDrop = (event: React.DragEvent) => {
        event.preventDefault()

        const serviceData = event.dataTransfer.getData('application/json')
        if (!serviceData) return

        const service: ServiceMetadata = JSON.parse(serviceData)
        const reactFlowBounds = event.currentTarget.getBoundingClientRect()
        const position = {
            x: event.clientX - reactFlowBounds.left,
            y: event.clientY - reactFlowBounds.top,
        }

        const newNode: Node = {
            id: generateId(),
            type: 'service',
            position,
            data: {
                service_type: service.service_id,
                display_name: service.display_name,
                category: service.category,
                config: {},
            },
        }

        setNodes((nds) => nds.concat(newNode))
    }

    const onDragOver = (event: React.DragEvent) => {
        event.preventDefault()
        event.dataTransfer.dropEffect = 'move'
    }

    const onNodeDoubleClick = (_event: any, node: Node) => {
        setSelectedNode(node)
        setConfigDialogOpen(true)
    }

    const saveNodeConfig = (config: Record<string, any>) => {
        if (!selectedNode) return

        setNodes((nds: Node[]) =>
            nds.map((node: Node) =>
                node.id === selectedNode.id
                    ? { ...node, data: { ...node.data, config } }
                    : node
            )
        )
    }

    // Get UI schema for selected node
    const getNodeUISchema = () => {
        if (!selectedNode || !services) return null
        const service = services.find((s: ServiceMetadata) => s.service_id === selectedNode.data.service_type)
        return service?.ui_schema || null
    }

    return (
        <div className="flex h-full">
            {/* Service Catalog Sidebar */}
            {showCatalog && (
                <div className="w-80 border-r border-border bg-card">
                    <ServiceCatalog services={services || []} />
                </div>
            )}

            {/* Main Canvas */}
            <div className="flex-1">
                <div className="flex h-full flex-col">
                    {/* Toolbar */}
                    <div className="flex items-center justify-between border-b border-border bg-card px-4 py-3">
                        <div>
                            <h2 className="font-semibold">{project?.name || 'Loading...'}</h2>
                            <p className="text-sm text-muted-foreground">{project?.description}</p>
                        </div>
                        <button
                            onClick={() => calculateMutation.mutate()}
                            disabled={calculateMutation.isPending || storeNodes.length === 0}
                            className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                        >
                            <Calculator className="h-4 w-4" />
                            {calculateMutation.isPending ? 'Calculating...' : 'Calculate Cost'}
                        </button>
                    </div>

                    {/* ReactFlow Canvas */}
                    <div className="flex-1">
                        <ReactFlow
                            nodes={nodes}
                            edges={edges}
                            onNodesChange={onNodesChange}
                            onEdgesChange={onEdgesChange}
                            onConnect={onConnect}
                            onDrop={onDrop}
                            onDragOver={onDragOver}
                            onNodeDoubleClick={onNodeDoubleClick}
                            nodeTypes={nodeTypes}
                            fitView
                        >
                            <Background />
                            <Controls />
                            <MiniMap />
                        </ReactFlow>
                    </div>
                </div>
            </div>

            {/* Estimate Summary Sidebar */}
            {estimate && (
                <div className="w-96 border-l border-border bg-card">
                    <EstimateSummary estimate={estimate} />
                </div>
            )}

            {/* Service Configuration Dialog */}
            {selectedNode && (
                <ServiceConfigDialog
                    isOpen={configDialogOpen}
                    onClose={() => setConfigDialogOpen(false)}
                    serviceType={selectedNode.data.service_type}
                    serviceName={selectedNode.data.display_name}
                    currentConfig={selectedNode.data.config || {}}
                    uiSchema={getNodeUISchema()}
                    onSave={saveNodeConfig}
                />
            )}
        </div>
    )
}
