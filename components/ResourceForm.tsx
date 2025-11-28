import React, { useState, useEffect } from 'react';
import { AWS_SERVICES } from '../constants';
import { InfrastructureResource, ServiceDefinition, FieldCategory } from '../types';
import {
  Plus, Server, Database, HardDrive, Network, Box, Layers,
  Globe, Lock, Activity, Zap, Shield, Key, RefreshCw, Router, HelpCircle, ChevronRight, ChevronDown, Info
} from 'lucide-react';

interface ResourceFormProps {
  onAddResource: (resource: InfrastructureResource) => void;
}

const CATEGORY_ORDER: FieldCategory[] = ['Basic', 'Compute', 'Storage', 'Network', 'Features', 'Advanced'];

const ResourceForm: React.FC<ResourceFormProps> = ({ onAddResource }) => {
  const [selectedServiceId, setSelectedServiceId] = useState<string>(AWS_SERVICES[0].id);
  const [formData, setFormData] = useState<Record<string, string | number | boolean>>({});
  const [expandedCategories, setExpandedCategories] = useState<Record<string, boolean>>({
    'Basic': true,
    'Compute': true,
    'Storage': true,
    'Network': true
  });

  const selectedService = AWS_SERVICES.find((s) => s.id === selectedServiceId) as ServiceDefinition;

  useEffect(() => {
    // Set defaults when service changes
    const defaults: Record<string, any> = {};
    selectedService.fields.forEach(f => {
      if (f.defaultValue !== undefined) {
        defaults[f.key] = f.defaultValue;
      }
    });
    setFormData(defaults);
    setExpandedCategories({
      'Basic': true,
      'Compute': true,
      'Storage': true,
      'Network': true,
      'Features': true,
      'Advanced': false
    });
  }, [selectedServiceId]);

  const handleInputChange = (key: string, value: string | number | boolean) => {
    setFormData((prev) => ({ ...prev, [key]: value }));
  };

  const toggleCategory = (cat: string) => {
    setExpandedCategories(prev => ({ ...prev, [cat]: !prev[cat] }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const newResource: InfrastructureResource = {
      id: Math.random().toString(36).substr(2, 9),
      serviceId: selectedService.id,
      serviceName: selectedService.name,
      config: formData,
    };
    onAddResource(newResource);
  };

  const renderIcon = (iconName: string, className: string) => {
    switch (iconName) {
      case 'Server': return <Server className={className} />;
      case 'Database': return <Database className={className} />;
      case 'HardDrive': return <HardDrive className={className} />;
      case 'Network': return <Network className={className} />;
      case 'Layers': return <Layers className={className} />;
      case 'Router': return <Router className={className} />;
      case 'Globe': return <Globe className={className} />;
      case 'Activity': return <Activity className={className} />;
      case 'Zap': return <Zap className={className} />;
      case 'Shield': return <Shield className={className} />;
      case 'Key': return <Key className={className} />;
      case 'RefreshCw': return <RefreshCw className={className} />;
      case 'Lock': return <Lock className={className} />;
      default: return <Box className={className} />;
    }
  };

  // Group fields by category
  const groupedFields = selectedService.fields.reduce((acc, field) => {
    const cat = field.category || 'Basic';
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(field);
    return acc;
  }, {} as Record<string, typeof selectedService.fields>);

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 flex flex-col w-full overflow-hidden">
      {/* Header & Service Selection */}
      <div className="p-5 border-b border-slate-100 bg-slate-50/50">
        <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
          Select Service
        </label>
        <div className="relative group">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            {renderIcon(selectedService.icon, "w-5 h-5 text-indigo-600 group-hover:scale-110 transition-transform")}
          </div>
          <select
            value={selectedServiceId}
            onChange={(e) => setSelectedServiceId(e.target.value)}
            className="block w-full pl-10 pr-4 py-3 text-sm font-medium border-slate-200 border rounded-lg focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 shadow-sm transition-all bg-white hover:border-slate-300 cursor-pointer"
          >
            {AWS_SERVICES.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>
        <p className="mt-3 text-xs text-slate-500 leading-relaxed flex items-start gap-2">
          <Info className="w-4 h-4 text-indigo-400 flex-shrink-0 mt-0.5" />
          {selectedService.description}
        </p>
      </div>

      {/* Scrollable Form Area */}
      <div className="flex-1 overflow-y-auto p-5 space-y-5 custom-scrollbar max-h-[600px] bg-white">
        <form id="resource-form" onSubmit={handleSubmit} className="space-y-5">
          {CATEGORY_ORDER.map((category) => {
            const fields = groupedFields[category];
            if (!fields || fields.length === 0) return null;

            const isExpanded = expandedCategories[category];

            return (
              <div key={category} className="border border-slate-100 rounded-lg overflow-hidden shadow-sm transition-all duration-300 hover:shadow-md">
                <button
                  type="button"
                  onClick={() => toggleCategory(category)}
                  className="w-full px-4 py-3 bg-slate-50 flex items-center justify-between text-left text-xs font-bold text-slate-700 uppercase tracking-wider hover:bg-slate-100 transition-colors"
                >
                  <span>{category} Configuration</span>
                  {isExpanded ? <ChevronDown className="w-4 h-4 text-slate-500" /> : <ChevronRight className="w-4 h-4 text-slate-500" />}
                </button>

                {isExpanded && (
                  <div className="p-4 bg-white grid grid-cols-1 md:grid-cols-2 gap-4 animate-in slide-in-from-top-2 duration-200">
                    {fields.map((field) => (
                      <div key={field.key} className={`flex flex-col ${field.type === 'select' ? 'md:col-span-1' : ''}`}>
                        <div className="flex items-center justify-between mb-1.5">
                          <label className="text-xs font-medium text-slate-700 flex items-center gap-1">
                            {field.label}
                            {field.optional && <span className="text-[10px] text-slate-400 font-normal italic bg-slate-100 px-1.5 py-0.5 rounded-full">Optional</span>}
                          </label>
                          {field.tooltip && (
                            <div className="group relative">
                              <HelpCircle className="w-3.5 h-3.5 text-slate-400 cursor-help hover:text-indigo-500 transition-colors" />
                              <div className="absolute right-0 bottom-full mb-1 w-56 p-2 bg-slate-800 text-white text-[11px] leading-tight rounded-md shadow-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-20">
                                {field.tooltip}
                                <div className="absolute bottom-[-4px] right-1 w-2 h-2 bg-slate-800 rotate-45"></div>
                              </div>
                            </div>
                          )}
                        </div>

                        {field.type === 'select' ? (
                          <div className="relative">
                            <select
                              className="w-full appearance-none rounded-md border-slate-200 border bg-slate-50/50 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all hover:bg-slate-50"
                              value={(formData[field.key] as string) || ''}
                              onChange={(e) => handleInputChange(field.key, e.target.value)}
                            >
                              {field.options?.map((opt) => (
                                <option key={opt} value={opt}>{opt}</option>
                              ))}
                            </select>
                            <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-slate-500">
                              <ChevronDown className="w-3 h-3" />
                            </div>
                          </div>
                        ) : (
                          <div className="relative group/input">
                            <input
                              type={field.type}
                              placeholder={field.placeholder}
                              className="w-full rounded-md border-slate-200 border px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all placeholder:text-slate-300"
                              value={formData[field.key]?.toString() || ''}
                              onChange={(e) => handleInputChange(field.key, field.type === 'number' ? parseFloat(e.target.value) : e.target.value)}
                            />
                            {field.unit && (
                              <span className="absolute right-3 top-2 text-xs text-slate-400 font-medium pointer-events-none bg-white pl-1 group-focus-within/input:text-indigo-500">
                                {field.unit}
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )
          })}
        </form>
      </div>

      {/* Footer Action */}
      <div className="p-5 border-t border-slate-100 bg-slate-50/50 rounded-b-xl">
        <button
          onClick={handleSubmit}
          className="w-full flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold py-3 px-4 rounded-lg shadow-sm transition-all active:scale-[0.98] ring-offset-2 focus:ring-2 ring-indigo-500 hover:shadow-md"
        >
          <Plus className="w-4 h-4" /> Add to Infrastructure
        </button>
      </div>
    </div>
  );
};

export default ResourceForm;