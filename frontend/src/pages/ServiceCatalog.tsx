import { useState } from 'react'
import { ServiceMetadata } from '@/lib/api'
import { Search, Server, Database, Network, Cloud, Shield, Code, Settings } from 'lucide-react'

interface ServiceCatalogProps {
    services: ServiceMetadata[]
    fullPage?: boolean
}

const categoryIcons: Record<string, any> = {
    Compute: Server,
    Database: Database,
    Networking: Network,
    Storage: Cloud,
    Security: Shield,
    Management: Settings,
    'Developer Tools': Code,
}

export function ServiceCatalog({ services, fullPage = false }: ServiceCatalogProps) {
    const [search, setSearch] = useState('')
    const [selectedCategory, setSelectedCategory] = useState<string | null>(null)

    const categories = Array.from(new Set(services.map((s) => s.category)))

    const filteredServices = services.filter((service) => {
        const matchesSearch = service.display_name.toLowerCase().includes(search.toLowerCase())
        const matchesCategory = !selectedCategory || service.category === selectedCategory
        return matchesSearch && matchesCategory
    })

    const onDragStart = (event: React.DragEvent, service: ServiceMetadata) => {
        event.dataTransfer.setData('application/json', JSON.stringify(service))
        event.dataTransfer.effectAllowed = 'move'
    }

    if (fullPage) {
        return (
            <div className="space-y-6">
                {/* Search and Filters */}
                <div className="flex items-center gap-4">
                    <div className="relative flex-1">
                        <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
                        <input
                            type="text"
                            placeholder="Search services..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="w-full rounded-lg border border-input bg-background py-3 pl-11 pr-4 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                        />
                    </div>
                </div>

                {/* Categories */}
                <div className="flex flex-wrap gap-2">
                    <button
                        onClick={() => setSelectedCategory(null)}
                        className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${!selectedCategory
                                ? 'bg-primary text-primary-foreground'
                                : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
                            }`}
                    >
                        All Services ({services.length})
                    </button>
                    {categories.map((category) => {
                        const count = services.filter((s) => s.category === category).length
                        return (
                            <button
                                key={category}
                                onClick={() => setSelectedCategory(category)}
                                className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${selectedCategory === category
                                        ? 'bg-primary text-primary-foreground'
                                        : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
                                    }`}
                            >
                                {category} ({count})
                            </button>
                        )
                    })}
                </div>

                {/* Services Grid */}
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {filteredServices.map((service) => {
                        const Icon = categoryIcons[service.category] || Server
                        return (
                            <div
                                key={service.service_id}
                                draggable
                                onDragStart={(e) => onDragStart(e, service)}
                                className="cursor-move rounded-lg border border-border bg-card p-6 transition-all hover:border-primary hover:shadow-md"
                            >
                                <div className="flex items-start gap-4">
                                    <div className="rounded-lg bg-primary/10 p-3">
                                        <Icon className="h-6 w-6 text-primary" />
                                    </div>
                                    <div className="flex-1">
                                        <h3 className="font-semibold text-foreground">{service.display_name}</h3>
                                        <p className="mt-1 text-sm text-muted-foreground line-clamp-2">
                                            {service.description}
                                        </p>
                                        <div className="mt-3 flex flex-wrap gap-1">
                                            {service.tags.slice(0, 3).map((tag) => (
                                                <span
                                                    key={tag}
                                                    className="rounded-full bg-secondary px-2 py-0.5 text-xs text-secondary-foreground"
                                                >
                                                    {tag}
                                                </span>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )
                    })}
                </div>

                {filteredServices.length === 0 && (
                    <div className="py-16 text-center">
                        <Server className="mx-auto h-12 w-12 text-muted-foreground" />
                        <h3 className="mt-4 text-lg font-semibold text-foreground">No services found</h3>
                        <p className="mt-2 text-sm text-muted-foreground">
                            Try adjusting your search or filters
                        </p>
                    </div>
                )}
            </div>
        )
    }

    // Sidebar view (original)
    return (
        <div className="flex h-full flex-col">
            <div className="border-b border-border p-4">
                <h3 className="mb-4 font-semibold">Service Catalog</h3>

                {/* Search */}
                <div className="relative mb-4">
                    <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <input
                        type="text"
                        placeholder="Search services..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="w-full rounded-lg border border-input bg-background py-2 pl-10 pr-4 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                    />
                </div>

                {/* Categories */}
                <div className="flex flex-wrap gap-2">
                    <button
                        onClick={() => setSelectedCategory(null)}
                        className={`rounded-lg px-3 py-1 text-xs font-medium transition-colors ${!selectedCategory
                                ? 'bg-primary text-primary-foreground'
                                : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
                            }`}
                    >
                        All
                    </button>
                    {categories.map((category) => (
                        <button
                            key={category}
                            onClick={() => setSelectedCategory(category)}
                            className={`rounded-lg px-3 py-1 text-xs font-medium transition-colors ${selectedCategory === category
                                    ? 'bg-primary text-primary-foreground'
                                    : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
                                }`}
                        >
                            {category}
                        </button>
                    ))}
                </div>
            </div>

            {/* Services List */}
            <div className="flex-1 overflow-auto p-4">
                <div className="space-y-2">
                    {filteredServices.map((service) => {
                        const Icon = categoryIcons[service.category] || Server
                        return (
                            <div
                                key={service.service_id}
                                draggable
                                onDragStart={(e) => onDragStart(e, service)}
                                className="cursor-move rounded-lg border border-border bg-card p-3 transition-colors hover:border-primary"
                            >
                                <div className="flex items-start gap-3">
                                    <div className="rounded-lg bg-primary/10 p-2">
                                        <Icon className="h-4 w-4 text-primary" />
                                    </div>
                                    <div className="flex-1">
                                        <div className="font-medium text-sm">{service.display_name}</div>
                                        <div className="text-xs text-muted-foreground line-clamp-2">
                                            {service.description}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )
                    })}
                </div>

                {filteredServices.length === 0 && (
                    <div className="py-8 text-center text-sm text-muted-foreground">
                        No services found
                    </div>
                )}
            </div>
        </div>
    )
}
