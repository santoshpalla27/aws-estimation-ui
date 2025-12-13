import { create } from 'zustand'
import { Node, Edge } from 'reactflow'
import { Estimate } from '@/lib/api'

interface ProjectStore {
    // Project state
    projectId: string | null
    setProjectId: (id: string | null) => void

    // Graph state (using ReactFlow types)
    nodes: Node[]
    edges: Edge[]
    setNodes: (nodes: Node[]) => void
    setEdges: (edges: Edge[]) => void
    addNode: (node: Node) => void
    updateNode: (id: string, updates: Partial<Node>) => void
    removeNode: (id: string) => void
    addEdge: (edge: Edge) => void
    removeEdge: (source: string, target: string) => void
    clearGraph: () => void

    // Estimate state
    estimate: Estimate | null
    isCalculating: boolean
    setEstimate: (estimate: Estimate | null) => void
    setIsCalculating: (isCalculating: boolean) => void

    // UI state
    selectedNodeId: string | null
    setSelectedNodeId: (id: string | null) => void
}

export const useProjectStore = create<ProjectStore>((set) => ({
    // Project state
    projectId: null,
    setProjectId: (id) => set({ projectId: id }),

    // Graph state
    nodes: [],
    edges: [],

    setNodes: (nodes) => set({ nodes }),
    setEdges: (edges) => set({ edges }),

    addNode: (node) =>
        set((state) => ({
            nodes: [...state.nodes, node],
        })),

    updateNode: (id, updates) =>
        set((state) => ({
            nodes: state.nodes.map((n) => (n.id === id ? { ...n, ...updates } : n)),
        })),

    removeNode: (id) =>
        set((state) => ({
            nodes: state.nodes.filter((n) => n.id !== id),
            edges: state.edges.filter((e) => e.source !== id && e.target !== id),
            selectedNodeId: state.selectedNodeId === id ? null : state.selectedNodeId,
        })),

    addEdge: (edge) =>
        set((state) => ({
            edges: [...state.edges, edge],
        })),

    removeEdge: (source, target) =>
        set((state) => ({
            edges: state.edges.filter((e) => !(e.source === source && e.target === target)),
        })),

    clearGraph: () =>
        set({
            nodes: [],
            edges: [],
            selectedNodeId: null,
            estimate: null,
        }),

    // Estimate state
    estimate: null,
    isCalculating: false,
    setEstimate: (estimate) => set({ estimate }),
    setIsCalculating: (isCalculating) => set({ isCalculating }),

    // UI state
    selectedNodeId: null,
    setSelectedNodeId: (id) => set({ selectedNodeId: id }),
}))
