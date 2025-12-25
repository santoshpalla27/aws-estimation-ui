import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

export interface UploadResponse {
    job_id: string;
    status: string;
    message: string;
}

export interface AnalysisResponse {
    job_id: string;
    status: string;
    total_monthly_cost: number;
    total_resources: number;
    supported_resources: number;
    unsupported_resources: number;
}

export interface ResultsResponse {
    job_id: string;
    status: string;
    total_monthly_cost: number;
    total_resources: number;
    supported_resources: number;
    unsupported_resources: number;
    breakdown_by_service: Record<string, number>;
    breakdown_by_region: Record<string, number>;
    resources: Array<{
        name: string;
        type: string;
        service: string;
        region: string;
        monthly_cost: number;
        pricing_details: any;
        warnings: string[];
    }>;
    warnings: string[];
    errors: Array<{
        resource: string;
        type: string;
        error: string;
    }>;
    pricing_version: number;
}

export const uploadFile = async (file: File): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post<UploadResponse>('/api/upload', formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
    });

    return response.data;
};

export const analyzeJob = async (jobId: string): Promise<AnalysisResponse> => {
    const response = await api.post<AnalysisResponse>(`/api/analyze/${jobId}`);
    return response.data;
};

export const getResults = async (jobId: string): Promise<ResultsResponse> => {
    const response = await api.get<ResultsResponse>(`/api/results/${jobId}`);
    return response.data;
};

export const getJobStatus = async (jobId: string): Promise<{ status: string }> => {
    const response = await api.get(`/api/status/${jobId}`);
    return response.data;
};

export default api;
