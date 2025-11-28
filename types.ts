export interface ResourceConfig {
  [key: string]: string | number | boolean;
}

export interface InfrastructureResource {
  id: string;
  serviceId: string;
  serviceName: string;
  config: ResourceConfig;
}

export interface ServiceDefinition {
  id: string;
  name: string;
  icon: string;
  description: string;
  fields: ServiceField[];
}

export type FieldCategory = 'Basic' | 'Compute' | 'Storage' | 'Network' | 'Advanced' | 'Features';

export interface ServiceField {
  key: string;
  label: string;
  type: 'select' | 'number' | 'text' | 'boolean';
  category: FieldCategory;
  options?: string[];
  unit?: string;
  placeholder?: string;
  optional?: boolean;
  defaultValue?: string | number | boolean;
  tooltip?: string; // For explaining complex AWS terms
}

export interface CostItem {
  resourceName: string;
  monthlyCost: number;
  explanation: string;
}

export interface CostEstimationResult {
  totalMonthlyCost: number;
  breakdown: CostItem[];
  currency: string;
  summary: string;
}
