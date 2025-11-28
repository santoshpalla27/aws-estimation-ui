import React from 'react';
import { CostEstimationResult } from '../types';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import { Activity, AlertCircle, TrendingUp } from 'lucide-react';

interface CostDashboardProps {
  estimation: CostEstimationResult | null;
  isLoading: boolean;
}

const COLORS = ['#4f46e5', '#0ea5e9', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981'];

const CostDashboard: React.FC<CostDashboardProps> = ({ estimation, isLoading }) => {
  if (isLoading) {
    return (
      <div className="h-full bg-white rounded-lg shadow-sm border border-slate-200 p-8 flex flex-col items-center justify-center min-h-[400px]">
        <div className="relative w-12 h-12">
          <div className="absolute top-0 left-0 w-full h-full border-4 border-indigo-100 rounded-full"></div>
          <div className="absolute top-0 left-0 w-full h-full border-4 border-indigo-600 rounded-full border-t-transparent animate-spin"></div>
        </div>
        <h3 className="mt-4 text-slate-800 font-semibold text-sm">Calculating Costs...</h3>
        <p className="text-slate-500 text-xs mt-1 text-center max-w-xs">
          Analyzing pricing models for configured resources.
        </p>
      </div>
    );
  }

  if (!estimation) {
    return (
      <div className="h-full bg-slate-50/50 rounded-lg border border-dashed border-slate-300 p-8 flex flex-col items-center justify-center min-h-[400px] text-center">
        <div className="w-12 h-12 bg-white rounded-full shadow-sm flex items-center justify-center mb-3">
          <TrendingUp className="w-6 h-6 text-slate-300" />
        </div>
        <h3 className="text-slate-700 font-medium text-sm">No Estimate Yet</h3>
        <p className="text-slate-400 text-xs mt-1 max-w-[250px]">
          Configure your infrastructure on the left and hit Calculate.
        </p>
      </div>
    );
  }

  const chartData = estimation.breakdown.map((item) => ({
    name: item.resourceName.split('-')[0].trim(), // Shorten name for legend
    fullName: item.resourceName,
    value: item.monthlyCost,
  }));

  return (
    <div className="space-y-4 h-full overflow-y-auto custom-scrollbar pr-2">
      {/* Total Cost Card */}
      <div className="bg-gradient-to-br from-indigo-600 to-violet-700 rounded-lg shadow-md text-white p-5">
        <div className="flex justify-between items-start">
            <div>
                <h2 className="text-indigo-100 text-xs font-semibold uppercase tracking-wide mb-1">Monthly Estimate</h2>
                <div className="flex items-baseline gap-1">
                    <span className="text-3xl font-bold">${estimation.totalMonthlyCost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                    <span className="text-indigo-200 font-medium text-sm">{estimation.currency}</span>
                </div>
            </div>
            <div className="bg-white/10 p-2 rounded-lg backdrop-blur-sm">
                <Activity className="w-5 h-5 text-white" />
            </div>
        </div>
        <div className="mt-3 pt-3 border-t border-white/10 text-xs text-indigo-50 leading-relaxed">
          {estimation.summary}
        </div>
      </div>

      {/* Breakdown List */}
      <div className="bg-white rounded-lg shadow-sm border border-slate-200 overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-100 bg-slate-50/50 flex justify-between items-center">
          <h3 className="text-xs font-semibold text-slate-700 uppercase tracking-wider">Cost Breakdown</h3>
          <span className="text-[10px] text-slate-400">USD/mo</span>
        </div>
        <div className="divide-y divide-slate-100">
          {estimation.breakdown.map((item, index) => (
            <div key={index} className="p-3 hover:bg-slate-50 transition-colors">
              <div className="flex justify-between items-start mb-1 gap-4">
                <span className="font-medium text-slate-800 text-sm">{item.resourceName}</span>
                <span className="font-bold text-slate-900 text-sm whitespace-nowrap">
                  ${item.monthlyCost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
              </div>
              <p className="text-xs text-slate-500 flex items-start gap-1.5 mt-1">
                <AlertCircle className="w-3 h-3 mt-0.5 shrink-0 text-slate-400" />
                {item.explanation}
              </p>
            </div>
          ))}
        </div>
      </div>
      
      {/* Chart Section - Only if we have multiple items */}
      {estimation.breakdown.length > 1 && (
        <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-4">
            <h3 className="text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">Distribution</h3>
            <div className="h-[200px] w-full text-xs">
            <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                <Pie
                    data={chartData}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={70}
                    paddingAngle={3}
                    dataKey="value"
                >
                    {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                </Pie>
                <Tooltip 
                    formatter={(value: number) => `$${value.toFixed(2)}`}
                    contentStyle={{ borderRadius: '6px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)', fontSize: '12px' }}
                />
                <Legend verticalAlign="bottom" height={36} iconType="circle" />
                </PieChart>
            </ResponsiveContainer>
            </div>
        </div>
      )}
    </div>
  );
};

export default CostDashboard;
