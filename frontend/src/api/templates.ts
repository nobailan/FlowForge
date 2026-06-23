import { apiGet } from './client';
import type { TemplateInfo, TemplateDetail } from '../types/evaluation';
import type { NodeTypeInfo } from '../types/canvas';

export const templatesApi = {
  list: () => apiGet<TemplateInfo[]>('/templates/'),

  get: (name: string) => apiGet<TemplateDetail>(`/templates/${name}`),

  listNodeTypes: () => apiGet<NodeTypeInfo[]>('/templates/node-types'),
};
