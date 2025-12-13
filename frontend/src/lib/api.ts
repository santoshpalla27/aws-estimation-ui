import axios from 'axios'

const API_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000'

export const api = axios.create({
    baseURL: `${API_URL}/api/v1`,
    headers: {
        'Content-Type': 'application/json',
    },
})

// Types
export interface Project {
    id: string
    name: string
    description: string | null
    metadata: Record<string, any>
    created_at: string
    updated_at: string
}

export interface ServiceNode {
    id: string
    service_type: string
    config: Record<string, any>
    region: string
    availability_zone?: string
    metadata: Record<string, any>
}

export interface DependencyEdge {
    source: string
    target: string
    type: string
    reason: string
    cost_impact?: Record<string, any>
    metadata: Record<string, any>
}

export interface CostBreakdown {
    dimension: string
    key: string
    value: number
    details?: Record<string, any>
}

export interface Estimate {
    id: string
    project_id: string
    graph_id: string | null
    total_monthly_cost: number
    breakdown: CostBreakdown[]
    warnings: string[]
    assumptions: string[]
    confidence: number | null
    created_at: string
}

export interface ServiceMetadata {
    service_id: string
    display_name: string
    description: string
    category: string
    icon_url?: string
    tags: string[]
    ui_schema?: any  // JSON Schema for service configuration form
}

// API functions
export const projectsApi = {
    list: () => api.get<Project[]>('/projects'),
    get: (id: string) => api.get<Project>(`/projects/${id}`),
    create: (data: Partial<Project>) => api.post<Project>('/projects', data),
    update: (id: string, data: Partial<Project>) => api.put<Project>(`/projects/${id}`, data),
    delete: (id: string) => api.delete(`/projects/${id}`),
}

export const estimatesApi = {
    create: (projectId: string, data: { services: ServiceNode[]; dependencies?: DependencyEdge[] }) =>
        api.post<Estimate>(`/estimates?project_id=${projectId}`, data),
    get: (id: string) => api.get<Estimate>(`/estimates/${id}`),
    listByProject: (projectId: string) => api.get<Estimate[]>(`/estimates/project/${projectId}`),
}

export const servicesApi = {
    list: (category?: string) => {
        const params = category ? { category } : {}
        return api.get<ServiceMetadata[]>('/services', { params })
    },
    get: (serviceId: string) => api.get(`/services/${serviceId}`),
    getUISchema: (serviceId: string) => api.get(`/services/${serviceId}/ui-schema`),
}

export const healthApi = {
    check: () => api.get('/health'),
}
