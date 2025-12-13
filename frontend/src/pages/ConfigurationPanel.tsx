import { useState } from 'react'
import { ServiceMetadata } from '@/lib/api'
import { Plus, Trash2, DollarSign, Settings as SettingsIcon } from 'lucide-react'
import { ServiceConfigDialog } from '@/components/ServiceConfigDialog'
import { useProjectStore } from '@/store/projectStore'
import { generateId } from '@/lib/utils'

interface ConfigurationPanelProps {
    services: ServiceMetadata[]
    onCalculateCost: () => void
    isCalculating: boolean
}

export function ConfigurationPanel({ services, onCalculateCost, isCalculating }: ConfigurationPanelProps) {
    const { nodes, setNodes, estimate } = useProjectStore()
    const [selectedService, setSelectedService] = useState<ServiceMetadata | null>(null)
    const [configDialogOpen, setConfigDialogOpen] = useState(false)
    const [editingNodeId, setEditingNodeId] = useState<string | null>(null)

    const handleAddService = (service: ServiceMetadata) => {
        const newNode = {
            id: generateId(),
            type: 'service',
            position: { x: Math.random() * 500, y: Math.random() * 300 },
            data: {
                service_type: service.service_id,
                display_name: service.display_name,
                category: service.category,
                config: {},
            },
        }
        setNodes([...nodes, newNode])

        // Open configuration dialog immediately
        setSelectedService(service)
        setEditingNodeId(newNode.id)
        setConfigDialogOpen(true)
    }

    const handleConfigureService = (nodeId: string) => {
        const node = nodes.find((n) => n.id === nodeId)
        if (node) {
            const service = services.find((s) => s.service_id === node.data.service_type)
            if (service) {
                setSelectedService(service)
                setEditingNodeId(nodeId)
                setConfigDialogOpen(true)
            }
        }
    }

    const handleRemoveService = (nodeId: string) => {
        setNodes(nodes.filter((n) => n.id !== nodeId))
    }

    const handleSaveConfig = (config: Record<string, any>) => {
        if (editingNodeId) {
            setNodes(
                nodes.map((node) =>
                    node.id === editingNodeId
                        ? { ...node, data: { ...node.data, config } }
                        : node
                )
            )
        }
    }

    // Group services by category
    const servicesByCategory = services.reduce((acc, service) => {
        if (!acc[service.category]) {
            acc[service.category] = []
        }
        acc[service.category].push(service)
        return acc
    }, {} as Record<string, ServiceMetadata[]>)

    // Calculate total cost from estimate
    const totalCost = estimate?.total_monthly_cost || 0

    return (
        <div className="flex h-full">
            {/* Left: Service Selection */}
            <div className="w-96 border-r border-border bg-card overflow-auto">
                <div className="p-4 border-b border-border">
                    <h3 className="font-semibold text-foreground">Add Services</h3>
                    <p className="text-sm text-muted-foreground mt-1">
                        Click to add services to your architecture
                    </p>
                </div>

                <div className="p-4 space-y-4">
                    {Object.entries(servicesByCategory).map(([category, categoryServices]) => (
                        <div key={category}>
                            <h4 className="text-sm font-medium text-foreground mb-2">{category}</h4>
                            <div className="space-y-1">
                                {categoryServices.map((service) => (
                                    <button
                                        key={service.service_id}
                                        onClick={() => handleAddService(service)}
                                        className="w-full flex items-center gap-3 p-3 rounded-lg border border-border bg-background hover:border-primary hover:bg-accent transition-colors text-left"
                                    >
                                        <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
                                            <Plus className="h-4 w-4 text-primary" />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="text-sm font-medium text-foreground truncate">
                                                {service.display_name}
                                            </div>
                                            <div className="text-xs text-muted-foreground truncate">
                                                {service.description}
                                            </div>
                                        </div>
                                    </button>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Right: Added Services & Cost */}
            <div className="flex-1 flex flex-col">
                {/* Header with Cost */}
                <div className="p-6 border-b border-border bg-card">
                    <div className="flex items-center justify-between">
                        <div>
                            <h3 className="text-lg font-semibold text-foreground">
                                Added Services ({nodes.length})
                            </h3>
                            <p className="text-sm text-muted-foreground mt-1">
                                Configure your services and calculate costs
                            </p>
                        </div>
                        <div className="text-right">
                            <div className="text-sm text-muted-foreground">Estimated Monthly Cost</div>
                            <div className="text-3xl font-bold text-primary mt-1">
                                ${totalCost.toFixed(2)}
                            </div>
                            <button
                                onClick={onCalculateCost}
                                disabled={isCalculating || nodes.length === 0}
                                className="mt-2 flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                            >
                                <DollarSign className="h-4 w-4" />
                                {isCalculating ? 'Calculating...' : 'Calculate Cost'}
                            </button>
                        </div>
                    </div>
                </div>

                {/* Services List */}
                <div className="flex-1 overflow-auto p-6">
                    {nodes.length === 0 ? (
                        <div className="flex h-full items-center justify-center">
                            <div className="text-center">
                                <SettingsIcon className="mx-auto h-16 w-16 text-muted-foreground" />
                                <h3 className="mt-4 text-lg font-semibold text-foreground">
                                    No Services Added
                                </h3>
                                <p className="mt-2 text-sm text-muted-foreground max-w-sm mx-auto">
                                    Click on a service from the left panel to add it to your architecture
                                </p>
                            </div>
                        </div>
                    ) : (
                        <div className="space-y-4 max-w-4xl">
                            {nodes.map((node) => {
                                const service = services.find((s) => s.service_id === node.data.service_type)
                                const hasConfig = Object.keys(node.data.config || {}).length > 0

                                return (
                                    <div
                                        key={node.id}
                                        className="rounded-lg border border-border bg-card p-4 hover:border-primary transition-colors"
                                    >
                                        <div className="flex items-start justify-between">
                                            <div className="flex-1">
                                                <div className="flex items-center gap-3">
                                                    <h4 className="font-semibold text-foreground">
                                                        {node.data.display_name}
                                                    </h4>
                                                    <span className="rounded-full bg-secondary px-2 py-0.5 text-xs text-secondary-foreground">
                                                        {node.data.category}
                                                    </span>
                                                    {hasConfig ? (
                                                        <span className="rounded-full bg-green-500/10 px-2 py-0.5 text-xs text-green-600 dark:text-green-400">
                                                            Configured
                                                        </span>
                                                    ) : (
                                                        <span className="rounded-full bg-yellow-500/10 px-2 py-0.5 text-xs text-yellow-600 dark:text-yellow-400">
                                                            Not Configured
                                                        </span>
                                                    )}
                                                </div>
                                                {service && (
                                                    <p className="text-sm text-muted-foreground mt-1">
                                                        {service.description}
                                                    </p>
                                                )}
                                                {hasConfig && (
                                                    <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
                                                        {Object.entries(node.data.config).slice(0, 4).map(([key, value]) => (
                                                            <div key={key} className="flex items-center gap-2">
                                                                <span className="text-muted-foreground">{key}:</span>
                                                                <span className="font-medium text-foreground">
                                                                    {String(value)}
                                                                </span>
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <button
                                                    onClick={() => handleConfigureService(node.id)}
                                                    className="rounded-lg p-2 hover:bg-accent transition-colors"
                                                    title="Configure"
                                                >
                                                    <SettingsIcon className="h-4 w-4 text-muted-foreground" />
                                                </button>
                                                <button
                                                    onClick={() => handleRemoveService(node.id)}
                                                    className="rounded-lg p-2 hover:bg-destructive/10 transition-colors"
                                                    title="Remove"
                                                >
                                                    <Trash2 className="h-4 w-4 text-destructive" />
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                )
                            })}
                        </div>
                    )}
                </div>

                {/* Cost Breakdown */}
                {estimate && (
                    <div className="border-t border-border bg-card p-6">
                        <h4 className="font-semibold text-foreground mb-3">Cost Breakdown</h4>
                        <div className="space-y-2">
                            {estimate.breakdown.slice(0, 5).map((item, index) => (
                                <div key={index} className="flex items-center justify-between text-sm">
                                    <span className="text-muted-foreground">{item.key}</span>
                                    <span className="font-medium text-foreground">
                                        ${Number(item.value).toFixed(2)}
                                    </span>
                                </div>
                            ))}
                        </div>
                        {estimate.warnings.length > 0 && (
                            <div className="mt-4 rounded-lg bg-yellow-500/10 p-3">
                                <div className="text-sm font-medium text-yellow-600 dark:text-yellow-400">
                                    Warnings
                                </div>
                                <ul className="mt-1 space-y-1 text-xs text-yellow-600/80 dark:text-yellow-400/80">
                                    {estimate.warnings.slice(0, 3).map((warning, index) => (
                                        <li key={index}>• {warning}</li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Configuration Dialog */}
            {selectedService && (
                <ServiceConfigDialog
                    isOpen={configDialogOpen}
                    onClose={() => {
                        setConfigDialogOpen(false)
                        setSelectedService(null)
                        setEditingNodeId(null)
                    }}
                    serviceType={selectedService.service_id}
                    serviceName={selectedService.display_name}
                    currentConfig={
                        editingNodeId
                            ? nodes.find((n) => n.id === editingNodeId)?.data.config || {}
                            : {}
                    }
                    uiSchema={selectedService.ui_schema}
                    onSave={handleSaveConfig}
                />
            )}
        </div>
    )
}
