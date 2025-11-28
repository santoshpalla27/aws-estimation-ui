import React from 'react';
import { InfrastructureResource } from '../types';
import { Trash2, Box, Layers, Settings2 } from 'lucide-react';

interface ResourceListProps {
  resources: InfrastructureResource[];
  onRemoveResource: (id: string) => void;
}

const ResourceList: React.FC<ResourceListProps> = ({ resources, onRemoveResource }) => {
  if (resources.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 border-dashed p-8 text-center flex flex-col items-center justify-center min-h-[160px]">
        <div className="w-12 h-12 bg-slate-50 rounded-full flex items-center justify-center mb-3">
          <Layers className="w-6 h-6 text-slate-300" />
        </div>
        <h3 className="text-slate-800 font-medium text-sm">Stack is empty</h3>
        <p className="text-xs text-slate-400 mt-1 max-w-[220px]">
          Add resources from the panel above to start building your infrastructure.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 flex flex-col overflow-hidden max-h-[500px]">
      <div className="px-4 py-3 border-b border-slate-100 bg-slate-50/80 backdrop-blur-sm flex justify-between items-center z-10 sticky top-0">
        <div className="flex items-center gap-2">
            <Layers className="w-3.5 h-3.5 text-slate-400" />
            <h2 className="text-xs font-bold text-slate-600 uppercase tracking-wider">Current Stack</h2>
        </div>
        <span className="bg-indigo-50 text-indigo-700 text-[10px] px-2 py-0.5 rounded-full font-bold border border-indigo-100 shadow-sm">
          {resources.length} {resources.length === 1 ? 'Resource' : 'Resources'}
        </span>
      </div>
      <div className="divide-y divide-slate-100 overflow-y-auto custom-scrollbar flex-1 p-1">
        {resources.map((resource) => (
          <div key={resource.id} className="p-3 hover:bg-slate-50 transition-all rounded-lg group relative mx-1 my-1 border border-transparent hover:border-slate-100">
            <div className="flex justify-between items-start pr-8">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 mb-1.5">
                    <h3 className="text-sm font-semibold text-slate-800 truncate">
                    {resource.serviceName}
                    </h3>
                </div>
                
                <div className="flex flex-wrap gap-1.5">
                  {Object.entries(resource.config).map(([key, value]) => {
                    if (value === '' || value === null || value === undefined) return null;
                    // Skip internal fields or empty numbers
                    if (typeof value === 'number' && value === 0) return null;
                    // Simplify display for long keys
                    const label = key.replace(/([A-Z])/g, ' $1').toLowerCase();
                    
                    return (
                        <span key={key} className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-600 border border-slate-200 max-w-full truncate">
                            <span className="opacity-50 mr-1">{label}:</span> 
                            <span className="truncate">{value.toString()}</span>
                        </span>
                    );
                  })}
                </div>
              </div>
            </div>
            <button
                onClick={() => onRemoveResource(resource.id)}
                className="absolute top-3 right-3 text-slate-300 hover:text-red-500 hover:bg-red-50 p-1.5 rounded-md transition-all opacity-0 group-hover:opacity-100"
                title="Remove Resource"
            >
                <Trash2 className="w-4 h-4" />
            </button>
          </div>
        ))}
        {/* Spacer for bottom scrolling */}
        <div className="h-2"></div>
      </div>
    </div>
  );
};

export default ResourceList;