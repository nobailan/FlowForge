import { apiGet, apiPost, apiPut, apiDelete } from './client';
import type { CanvasData } from '../types/canvas';

export interface ArchitectureSummary {
  id: string;
  name: string;
  description: string;
  created_at?: string;
  updated_at?: string;
}

export interface ArchitectureDetail extends ArchitectureSummary {
  canvas_data: CanvasData;
  metadata: Record<string, any>;
}

export const graphsApi = {
  list: () => apiGet<ArchitectureSummary[]>('/graphs/'),

  create: (name: string, description: string, canvas_data: CanvasData) =>
    apiPost<ArchitectureDetail>('/graphs/', { name, description, canvas_data }),

  get: (id: string) => apiGet<ArchitectureDetail>(`/graphs/${id}`),

  update: (id: string, data: Partial<{ name: string; description: string; canvas_data: CanvasData }>) =>
    apiPut<ArchitectureDetail>(`/graphs/${id}`, data),

  delete: (id: string) => apiDelete(`/graphs/${id}`),

  duplicate: (id: string) => apiPost<ArchitectureDetail>(`/graphs/${id}/duplicate`),
};
