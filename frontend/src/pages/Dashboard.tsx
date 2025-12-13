import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Plus, FolderOpen } from 'lucide-react'
import { projectsApi, Project } from '@/lib/api'
import { formatDate, formatCurrency } from '@/lib/utils'

export function Dashboard() {
    const navigate = useNavigate()

    const { data: projects, isLoading } = useQuery({
        queryKey: ['projects'],
        queryFn: async () => {
            const response = await projectsApi.list()
            return response.data
        },
    })

    const handleCreateProject = async () => {
        try {
            const response = await projectsApi.create({
                name: 'New Project',
                description: 'AWS infrastructure design',
                metadata: {},
            })
            navigate(`/projects/${response.data.id}`)
        } catch (error) {
            console.error('Failed to create project:', error)
        }
    }

    if (isLoading) {
        return (
            <div className="flex h-full items-center justify-center">
                <div className="text-muted-foreground">Loading projects...</div>
            </div>
        )
    }

    return (
        <div className="h-full overflow-auto p-8">
            <div className="mx-auto max-w-7xl">
                <div className="mb-8 flex items-center justify-between">
                    <div>
                        <h1 className="text-3xl font-bold">Projects</h1>
                        <p className="mt-2 text-muted-foreground">
                            Design and estimate AWS infrastructure costs
                        </p>
                    </div>
                    <button
                        onClick={handleCreateProject}
                        className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
                    >
                        <Plus className="h-4 w-4" />
                        New Project
                    </button>
                </div>

                {projects && projects.length > 0 ? (
                    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                        {projects.map((project: Project) => (
                            <div
                                key={project.id}
                                onClick={() => navigate(`/projects/${project.id}`)}
                                className="cursor-pointer rounded-lg border border-border bg-card p-6 transition-colors hover:border-primary"
                            >
                                <div className="mb-4 flex items-start justify-between">
                                    <FolderOpen className="h-8 w-8 text-primary" />
                                </div>
                                <h3 className="mb-2 font-semibold">{project.name}</h3>
                                <p className="mb-4 text-sm text-muted-foreground line-clamp-2">
                                    {project.description || 'No description'}
                                </p>
                                <div className="text-xs text-muted-foreground">
                                    Updated {formatDate(project.updated_at)}
                                </div>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-border py-16">
                        <FolderOpen className="mb-4 h-12 w-12 text-muted-foreground" />
                        <h3 className="mb-2 font-semibold">No projects yet</h3>
                        <p className="mb-4 text-sm text-muted-foreground">
                            Create your first project to get started
                        </p>
                        <button
                            onClick={handleCreateProject}
                            className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
                        >
                            <Plus className="h-4 w-4" />
                            New Project
                        </button>
                    </div>
                )}
            </div>
        </div>
    )
}
