import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Layers, Settings, ArrowLeft } from 'lucide-react'
import { projectsApi, servicesApi } from '@/lib/api'
import { ServiceCatalog } from './ServiceCatalog'
import { ProjectEditor } from './ProjectEditor'

type ViewMode = 'catalog' | 'architecture' | 'configuration'

export function ProjectWorkspace() {
    const { projectId } = useParams<{ projectId: string }>()
    const navigate = useNavigate()
    const [viewMode, setViewMode] = useState<ViewMode>('catalog')

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

    return (
        <div className="flex h-screen flex-col bg-background">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-border bg-card px-6 py-4">
                <div className="flex items-center gap-4">
                    <button
                        onClick={() => navigate('/')}
                        className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
                    >
                        <ArrowLeft className="h-4 w-4" />
                        Back to Projects
                    </button>
                    <div className="h-6 w-px bg-border" />
                    <div>
                        <h1 className="text-lg font-semibold text-foreground">{project?.name || 'Loading...'}</h1>
                        <p className="text-sm text-muted-foreground">{project?.description}</p>
                    </div>
                </div>

                {/* View Mode Tabs */}
                <div className="flex items-center gap-2 rounded-lg bg-muted p-1">
                    <button
                        onClick={() => setViewMode('catalog')}
                        className={`flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors ${viewMode === 'catalog'
                            ? 'bg-background text-foreground shadow-sm'
                            : 'text-muted-foreground hover:text-foreground'
                            }`}
                    >
                        <Layers className="h-4 w-4" />
                        Services Catalog
                    </button>
                    <button
                        onClick={() => setViewMode('architecture')}
                        className={`flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors ${viewMode === 'architecture'
                            ? 'bg-background text-foreground shadow-sm'
                            : 'text-muted-foreground hover:text-foreground'
                            }`}
                    >
                        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
                        </svg>
                        Architecture
                    </button>
                    <button
                        onClick={() => setViewMode('configuration')}
                        className={`flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors ${viewMode === 'configuration'
                            ? 'bg-background text-foreground shadow-sm'
                            : 'text-muted-foreground hover:text-foreground'
                            }`}
                    >
                        <Settings className="h-4 w-4" />
                        Configuration
                    </button>
                </div>
            </div>

            {/* Content Area */}
            <div className="flex-1 overflow-hidden">
                {viewMode === 'catalog' && (
                    <div className="h-full overflow-auto p-6">
                        <div className="mx-auto max-w-6xl">
                            <div className="mb-6">
                                <h2 className="text-2xl font-bold text-foreground">AWS Services Catalog</h2>
                                <p className="mt-2 text-muted-foreground">
                                    Browse and explore available AWS services. Click on a service to add it to your architecture.
                                </p>
                            </div>
                            <ServiceCatalog services={services || []} fullPage={true} />
                        </div>
                    </div>
                )}

                {viewMode === 'architecture' && (
                    <ProjectEditor />
                )}

                {viewMode === 'configuration' && (
                    <div className="flex h-full items-center justify-center">
                        <div className="text-center">
                            <Settings className="mx-auto h-16 w-16 text-muted-foreground" />
                            <h3 className="mt-4 text-lg font-semibold text-foreground">Service Configuration</h3>
                            <p className="mt-2 text-sm text-muted-foreground">
                                Double-click any service in the Architecture view to configure it
                            </p>
                            <button
                                onClick={() => setViewMode('architecture')}
                                className="mt-4 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
                            >
                                Go to Architecture
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}
