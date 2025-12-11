import React, { useState, useEffect } from 'react'
import { Filter, ChevronLeft, ChevronRight, Search } from 'lucide-react'

export default function Catalog({ serviceId }) {
    const [data, setData] = useState([])
    const [total, setTotal] = useState(0)
    const [page, setPage] = useState(1)
    const [loading, setLoading] = useState(false)
    const [filters, setFilters] = useState({})
    const [metadata, setMetadata] = useState({})
    const [pageSize, setPageSize] = useState(25)

    // Load metadata for filters
    useEffect(() => {
        fetch(`/api/pricing/metadata/${serviceId}`)
            .then(res => res.json())
            .then(data => setMetadata(data))
            .catch(err => console.error("Failed to load metadata", err))

        // Reset state on service change
        setFilters({})
        setPage(1)
        setData([])
    }, [serviceId])

    // Load catalog data
    useEffect(() => {
        setLoading(true)
        const query = new URLSearchParams({
            page: page,
            pageSize: pageSize,
            ...filters
        })

        // Remove empty filters
        Object.keys(filters).forEach(key => {
            if (!filters[key]) query.delete(key)
        })

        fetch(`/api/pricing/catalog/${serviceId}?${query.toString()}`)
            .then(res => res.json())
            .then(res => {
                setData(res.items || [])
                setTotal(res.total || 0)
                setLoading(false)
            })
            .catch(err => {
                console.error("Failed to load catalog", err)
                setLoading(false)
            })
    }, [serviceId, page, pageSize, filters])

    const handleFilterChange = (key, value) => {
        setFilters(prev => ({ ...prev, [key]: value }))
        setPage(1) // Reset to page 1 on filter change
    }

    const totalPages = Math.ceil(total / pageSize)

    // Helper to get columns from data
    const getColumns = () => {
        if (data.length === 0) return []
        // Combine all keys from all items to cover sparse data
        const keys = new Set()
        data.forEach(item => Object.keys(item).forEach(k => keys.add(k)))

        // Priority columns
        const priority = ['sku', 'price', 'location', 'instanceType', 'storageClass', 'vcpu', 'memory']
        const sorted = Array.from(keys).sort((a, b) => {
            const idxA = priority.indexOf(a)
            const idxB = priority.indexOf(b)
            if (idxA !== -1 && idxB !== -1) return idxA - idxB
            if (idxA !== -1) return -1
            if (idxB !== -1) return 1
            return a.localeCompare(b)
        })
        return sorted.filter(k => k !== 'attributes') // attributes is flattened or ignored if we use flat dicts
    }

    // Flatten attributes for display?
    // The backend returns { sku, price, location, ...attributes } flattened?
    // No, backend returns:
    // item = json.loads(row['attributes'])
    // item['sku'] = ...
    // So yes, it is flattened.

    return (
        <div className="catalog-container">
            <div className="filters-bar" style={{
                display: 'flex', gap: '1rem', padding: '1rem',
                background: 'var(--bg-secondary)', borderRadius: 'var(--radius)',
                marginBottom: '1rem', flexWrap: 'wrap'
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', opacity: 0.7 }}>
                    <Filter size={16} /> Filters:
                </div>

                {/* Dynamic Filters based on metadata */}
                {metadata.locations && (
                    <select className="input small" onChange={e => handleFilterChange('location', e.target.value)} value={filters.location || ''}>
                        <option value="">All Regions</option>
                        {metadata.locations.map(v => <option key={v} value={v}>{v}</option>)}
                    </select>
                )}

                {metadata.instanceTypes && (
                    <select className="input small" onChange={e => handleFilterChange('instanceType', e.target.value)} value={filters.instanceType || ''}>
                        <option value="">All Types</option>
                        {metadata.instanceTypes.map(v => <option key={v} value={v}>{v}</option>)}
                    </select>
                )}

                {/* Generic Search for SKU */}
                <div style={{ position: 'relative' }}>
                    <Search size={14} style={{ position: 'absolute', left: 8, top: 9, opacity: 0.5 }} />
                    <input
                        className="input small"
                        placeholder="Search SKU..."
                        style={{ paddingLeft: '24px' }}
                        onChange={e => handleFilterChange('sku', e.target.value)}
                        value={filters.sku || ''}
                    />
                </div>
            </div>

            <div className="table-wrapper" style={{ overflowX: 'auto', background: 'var(--bg-secondary)', borderRadius: 'var(--radius)' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
                    <thead>
                        <tr style={{ borderBottom: '1px solid var(--border)', textAlign: 'left' }}>
                            {getColumns().map(col => (
                                <th key={col} style={{ padding: '0.75rem' }}>{col.toUpperCase()}</th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {loading ? (
                            <tr><td colSpan="100" style={{ padding: '2rem', textAlign: 'center' }}>Loading...</td></tr>
                        ) : data.length === 0 ? (
                            <tr><td colSpan="100" style={{ padding: '2rem', textAlign: 'center' }}>No results found.</td></tr>
                        ) : (
                            data.map((row, idx) => (
                                <tr key={row.sku || idx} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                                    {getColumns().map(col => (
                                        <td key={col} style={{ padding: '0.75rem', whiteSpace: 'nowrap' }}>
                                            {col === 'price' ? `$${parseFloat(row[col] || 0).toFixed(4)}` : row[col]?.toString()}
                                        </td>
                                    ))}
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>

            <div className="pagination" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '1rem' }}>
                <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                    Showing {(page - 1) * pageSize + 1} - {Math.min(page * pageSize, total)} of {total} items
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button
                        className="btn small secondary"
                        disabled={page === 1}
                        onClick={() => setPage(p => p - 1)}
                    >
                        <ChevronLeft size={16} /> Prev
                    </button>
                    <span style={{ display: 'flex', alignItems: 'center', padding: '0 0.5rem' }}>
                        Page {page} of {totalPages || 1}
                    </span>
                    <button
                        className="btn small secondary"
                        disabled={page >= totalPages}
                        onClick={() => setPage(p => p + 1)}
                    >
                        Next <ChevronRight size={16} />
                    </button>
                </div>
            </div>
        </div>
    )
}
