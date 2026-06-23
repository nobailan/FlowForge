import { apiGet, apiPost } from './client';
import type { CanvasData } from '../types/canvas';
import type { ExecuteResponse, ExecutionResult, NodeEvent } from '../types/execution';

export const executeApi = {
  run: (canvas_data: CanvasData, input_text: string) =>
    apiPost<ExecuteResponse>('/execute/', { canvas_data, input_text }),

  getResult: (executionId: string) =>
    apiGet<ExecutionResult>(`/execute/${executionId}`),

  getEvents: (executionId: string) =>
    apiGet<NodeEvent[]>(`/execute/${executionId}/events`),
};
