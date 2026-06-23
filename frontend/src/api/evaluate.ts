import { apiGet, apiPost } from './client';
import type { EvaluationResult, CompareResult } from '../types/evaluation';

export const evaluateApi = {
  run: (architecture_id: string, testset_id: string) =>
    apiPost<EvaluationResult>('/evaluate/', { architecture_id, testset_id }),

  getResult: (runId: string) =>
    apiGet<EvaluationResult>(`/evaluate/runs/${runId}`),

  listRuns: (architectureId?: string) =>
    apiGet<EvaluationResult[]>(`/evaluate/runs${architectureId ? `?architecture_id=${architectureId}` : ''}`),

  compare: (evalRunIds: string[]) =>
    apiPost<CompareResult>('/evaluate/compare', { eval_run_ids: evalRunIds }),

  listTestSets: () =>
    apiGet<{ id: string; name: string; description: string; test_cases: any[] }[]>('/evaluate/test-sets'),

  createTestSet: (name: string, description: string, test_cases: any[]) =>
    apiPost('/evaluate/test-sets', { name, description, test_cases }),
};
