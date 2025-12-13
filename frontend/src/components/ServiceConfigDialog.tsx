import { useState } from 'react'
import { X } from 'lucide-react'

interface ServiceConfigDialogProps {
    isOpen: boolean
    onClose: () => void
    serviceType: string
    serviceName: string
    currentConfig: Record<string, any>
    uiSchema: any
    onSave: (config: Record<string, any>) => void
}

export function ServiceConfigDialog({
    isOpen,
    onClose,
    serviceType,
    serviceName,
    currentConfig,
    uiSchema,
    onSave,
}: ServiceConfigDialogProps) {
    const [config, setConfig] = useState<Record<string, any>>(currentConfig || {})

    if (!isOpen) return null

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault()
        onSave(config)
        onClose()
    }

    const handleChange = (field: string, value: any) => {
        setConfig((prev) => ({ ...prev, [field]: value }))
    }

    const renderField = (fieldName: string, fieldSchema: any) => {
        const value = config[fieldName] ?? fieldSchema.default

        // Number input
        if (fieldSchema.type === 'number' || fieldSchema.type === 'integer') {
            return (
                <div key={fieldName} className="mb-4">
                    <label className="block text-sm font-medium text-foreground mb-1">
                        {fieldSchema.title || fieldName}
                    </label>
                    {fieldSchema.description && (
                        <p className="text-xs text-muted-foreground mb-2">{fieldSchema.description}</p>
                    )}
                    <input
                        type="number"
                        value={value || ''}
                        onChange={(e) => handleChange(fieldName, fieldSchema.type === 'integer' ? parseInt(e.target.value) : parseFloat(e.target.value))}
                        min={fieldSchema.minimum}
                        max={fieldSchema.maximum}
                        step={fieldSchema.type === 'integer' ? 1 : 'any'}
                        className="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                </div>
            )
        }

        // String input
        if (fieldSchema.type === 'string' && !fieldSchema.enum) {
            return (
                <div key={fieldName} className="mb-4">
                    <label className="block text-sm font-medium text-foreground mb-1">
                        {fieldSchema.title || fieldName}
                    </label>
                    {fieldSchema.description && (
                        <p className="text-xs text-muted-foreground mb-2">{fieldSchema.description}</p>
                    )}
                    <input
                        type="text"
                        value={value || ''}
                        onChange={(e) => handleChange(fieldName, e.target.value)}
                        className="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                </div>
            )
        }

        // Select dropdown (enum)
        if (fieldSchema.enum) {
            return (
                <div key={fieldName} className="mb-4">
                    <label className="block text-sm font-medium text-foreground mb-1">
                        {fieldSchema.title || fieldName}
                    </label>
                    {fieldSchema.description && (
                        <p className="text-xs text-muted-foreground mb-2">{fieldSchema.description}</p>
                    )}
                    <select
                        value={value || fieldSchema.default}
                        onChange={(e) => handleChange(fieldName, e.target.value)}
                        className="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                    >
                        {fieldSchema.enum.map((option: string, index: number) => (
                            <option key={option} value={option}>
                                {fieldSchema.enumNames?.[index] || option}
                            </option>
                        ))}
                    </select>
                </div>
            )
        }

        // Boolean checkbox
        if (fieldSchema.type === 'boolean') {
            return (
                <div key={fieldName} className="mb-4 flex items-start">
                    <input
                        type="checkbox"
                        checked={value || false}
                        onChange={(e) => handleChange(fieldName, e.target.checked)}
                        className="mt-1 h-4 w-4 text-primary border-border rounded focus:ring-primary"
                    />
                    <div className="ml-3">
                        <label className="text-sm font-medium text-foreground">
                            {fieldSchema.title || fieldName}
                        </label>
                        {fieldSchema.description && (
                            <p className="text-xs text-muted-foreground">{fieldSchema.description}</p>
                        )}
                    </div>
                </div>
            )
        }

        // Object (nested fields)
        if (fieldSchema.type === 'object' && fieldSchema.properties) {
            return (
                <div key={fieldName} className="mb-4 p-4 border border-border rounded-lg">
                    <h4 className="text-sm font-medium text-foreground mb-3">{fieldSchema.title || fieldName}</h4>
                    {Object.entries(fieldSchema.properties).map(([nestedField, nestedSchema]: [string, any]) =>
                        renderField(`${fieldName}.${nestedField}`, nestedSchema)
                    )}
                </div>
            )
        }

        return null
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
            <div className="bg-card border border-border rounded-lg shadow-lg w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b border-border">
                    <div>
                        <h2 className="text-lg font-semibold text-foreground">Configure {serviceName}</h2>
                        <p className="text-sm text-muted-foreground">{serviceType}</p>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-accent rounded-lg transition-colors"
                    >
                        <X className="h-5 w-5" />
                    </button>
                </div>

                {/* Form */}
                <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-4">
                    {uiSchema?.properties && Object.entries(uiSchema.properties).map(([fieldName, fieldSchema]: [string, any]) =>
                        renderField(fieldName, fieldSchema)
                    )}
                </form>

                {/* Footer */}
                <div className="flex items-center justify-end gap-3 p-4 border-t border-border">
                    <button
                        type="button"
                        onClick={onClose}
                        className="px-4 py-2 text-sm font-medium text-foreground hover:bg-accent rounded-lg transition-colors"
                    >
                        Cancel
                    </button>
                    <button
                        type="submit"
                        onClick={handleSubmit}
                        className="px-4 py-2 text-sm font-medium bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
                    >
                        Save Configuration
                    </button>
                </div>
            </div>
        </div>
    )
}
