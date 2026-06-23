import { create } from 'zustand';
import type { NodeEvent, ExecutionResult } from '../types/execution';
import type { EvaluationResult, EvalSummary } from '../types/evaluation';

export type RightPanelMode = 'config' | 'monitor' | 'eval' | 'compare' | 'library' | null;

interface AppStore {
  // Architecture lifecycle
  currentArchitectureId: string | null;
  architectureName: string;
  isDirty: boolean;
  setArchitectureId: (id: string | null) => void;
  setArchitectureName: (name: string) => void;
  markDirty: (dirty: boolean) => void;

  // Right panel mode
  rightPanelMode: RightPanelMode;
  setRightPanel: (mode: RightPanelMode) => void;

  // Execution
  executionId: string | null;
  executionStatus: 'idle' | 'running' | 'completed' | 'error';
  nodeEvents: NodeEvent[];
  setExecutionId: (id: string | null) => void;
  setExecutionStatus: (status: string) => void;
  addNodeEvent: (event: NodeEvent) => void;
  clearExecution: () => void;

  // Evaluation
  evalRunId: string | null;
  evalResults: EvalSummary | null;
  evalDetailResults: EvaluationResult | null;
  setEvalRunId: (id: string | null) => void;
  setEvalResults: (results: EvalSummary | null) => void;
  setEvalDetailResults: (results: EvaluationResult | null) => void;
}

export const useAppStore = create<AppStore>((set, get) => ({
  currentArchitectureId: null,
  architectureName: 'Untitled Flow',
  isDirty: false,
  setArchitectureId: (id) => set({ currentArchitectureId: id }),
  setArchitectureName: (name) => set({ architectureName: name }),
  markDirty: (dirty) => set({ isDirty: dirty }),

  rightPanelMode: null,
  setRightPanel: (mode) => set({ rightPanelMode: mode }),

  executionId: null,
  executionStatus: 'idle',
  nodeEvents: [],
  setExecutionId: (id) => set({ executionId: id }),
  setExecutionStatus: (status) =>
    set({ executionStatus: status as AppStore['executionStatus'] }),
  addNodeEvent: (event) =>
    set({ nodeEvents: [...get().nodeEvents, event] }),
  clearExecution: () =>
    set({ executionId: null, executionStatus: 'idle', nodeEvents: [] }),

  evalRunId: null,
  evalResults: null,
  evalDetailResults: null,
  setEvalRunId: (id) => set({ evalRunId: id }),
  setEvalResults: (results) => set({ evalResults: results }),
  setEvalDetailResults: (results) => set({ evalDetailResults: results }),
}));
