import { Estimate } from '@/lib/api'
import { formatCurrency } from '@/lib/utils'
import { DollarSign, AlertTriangle, Info, TrendingUp } from 'lucide-react'

interface EstimateSummaryProps {
    estimate: Estimate
}

export function EstimateSummary({ estimate }: EstimateSummaryProps) {
    const confidenceColor = estimate.confidence
        ? estimate.confidence >= 0.8
            ? 'text-green-600'
            : estimate.confidence >= 0.6
                ? 'text-yellow-600'
                : 'text-red-600'
        : 'text-muted-foreground'

    return (
        <div className="flex h-full flex-col">
            <div className="border-b border-border p-4">
                <h3 className="font-semibold">Cost Estimate</h3>
            </div>

            <div className="flex-1 overflow-auto p-4">
                {/* Total Cost */}
                <div className="mb-6 rounded-lg border border-border bg-card p-4">
                    <div className="mb-2 flex items-center gap-2 text-sm text-muted-foreground">
                        <DollarSign className="h-4 w-4" />
                        <span>Total Monthly Cost</span>
                    </div>
                    <div className="text-3xl font-bold">
                        {formatCurrency(estimate.total_monthly_cost)}
                    </div>
                    {estimate.confidence !== null && (
                        <div className={`mt-2 text-sm ${confidenceColor}`}>
                            Confidence: {(estimate.confidence * 100).toFixed(0)}%
                        </div>
                    )}
                </div>

                {/* Breakdown */}
                <div className="mb-6">
                    <h4 className="mb-3 flex items-center gap-2 text-sm font-semibold">
                        <TrendingUp className="h-4 w-4" />
                        Cost Breakdown
                    </h4>
                    <div className="space-y-2">
                        {estimate.breakdown.map((item, index) => (
                            <div
                                key={index}
                                className="flex items-center justify-between rounded-lg border border-border bg-card p-3"
                            >
                                <div>
                                    <div className="font-medium text-sm">{item.key}</div>
                                    <div className="text-xs text-muted-foreground capitalize">
                                        {item.dimension}
                                    </div>
                                </div>
                                <div className="font-semibold">{formatCurrency(item.value)}</div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Warnings */}
                {estimate.warnings.length > 0 && (
                    <div className="mb-6">
                        <h4 className="mb-3 flex items-center gap-2 text-sm font-semibold text-yellow-600">
                            <AlertTriangle className="h-4 w-4" />
                            Warnings
                        </h4>
                        <div className="space-y-2">
                            {estimate.warnings.map((warning, index) => (
                                <div
                                    key={index}
                                    className="rounded-lg border border-yellow-200 bg-yellow-50 p-3 text-sm text-yellow-800"
                                >
                                    {warning}
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Assumptions */}
                {estimate.assumptions.length > 0 && (
                    <div>
                        <h4 className="mb-3 flex items-center gap-2 text-sm font-semibold">
                            <Info className="h-4 w-4" />
                            Assumptions
                        </h4>
                        <div className="space-y-2">
                            {estimate.assumptions.map((assumption, index) => (
                                <div
                                    key={index}
                                    className="rounded-lg border border-border bg-card p-3 text-sm text-muted-foreground"
                                >
                                    {assumption}
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}
