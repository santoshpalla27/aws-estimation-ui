import { Handle, Position } from 'reactflow'
import { Server, Database, Network, Cloud } from 'lucide-react'

interface ServiceNodeProps {
    data: {
        service_type: string
        display_name: string
        category: string
        config: Record<string, any>
    }
}

const categoryIcons: Record<string, any> = {
    Compute: Server,
    Database: Database,
    Networking: Network,
    Storage: Cloud,
}

export function ServiceNode({ data }: ServiceNodeProps) {
    const Icon = categoryIcons[data.category] || Server

    return (
        <div className="min-w-[200px] rounded-lg border-2 border-border bg-card p-4 shadow-md">
            <Handle type="target" position={Position.Left} className="!bg-primary" />

            <div className="flex items-start gap-3">
                <div className="rounded-lg bg-primary/10 p-2">
                    <Icon className="h-5 w-5 text-primary" />
                </div>
                <div className="flex-1">
                    <div className="font-semibold">{data.display_name}</div>
                    <div className="text-xs text-muted-foreground">{data.category}</div>
                </div>
            </div>

            {Object.keys(data.config).length > 0 && (
                <div className="mt-3 space-y-1 border-t border-border pt-3">
                    {Object.entries(data.config).slice(0, 3).map(([key, value]) => (
                        <div key={key} className="flex justify-between text-xs">
                            <span className="text-muted-foreground">{key}:</span>
                            <span className="font-medium">{String(value)}</span>
                        </div>
                    ))}
                </div>
            )}

            <Handle type="source" position={Position.Right} className="!bg-primary" />
        </div>
    )
}
