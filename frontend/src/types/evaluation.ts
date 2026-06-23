// ==================== Evaluation Types ====================

export interface EvalSummary {
  success_rate: number;
  avg_latency_ms: number;
  avg_tokens: number;
  total_cost_estimate: number;
  total_questions: number;
  passed: number;
  failed: number;
  // v0.2 Agent metrics
  total_tool_calls: number;
  total_tool_errors: number;
  tool_success_rate: number;
  avg_tool_calls_per_question: number;
  max_latency_ms: number;
  min_latency_ms: number;
}

export interface EvalDetail {
  test_id: number;
  question: string;
  category?: string;
  success: boolean;
  latency_ms: number;
  tokens: number;
  output: string;
  error: string;
  // v0.2 Agent metrics
  tool_calls: number;
  tool_errors: number;
  tool_call_log: ToolCallLogEntry[];
}

export interface ToolCallLogEntry {
  type: string;
  [key: string]: any;
}

export interface EvaluationResult {
  id: string;
  architecture_id: string;
  testset_name: string;
  status: string;
  summary: EvalSummary;
  detail_results: EvalDetail[];
  started_at?: string;
  completed_at?: string;
}

export interface CompareResult {
  runs: EvaluationResult[];
  diff: Record<string, any>;
  comparison_table?: ComparisonRow[];
  diffs?: DiffRow[];
}

export interface ComparisonRow {
  name: string;
  success_rate: number;
  avg_latency_ms: number;
  avg_tokens: number;
  total_cost: number;
  passed: number;
  failed: number;
  // v0.2
  total_tool_calls: number;
  tool_success_rate: number;
  avg_tool_calls_per_question: number;
}

export interface DiffRow {
  comparison: string;
  success_rate_delta: number;
  latency_delta_ms: number;
  tokens_delta: number;
  cost_delta: number;
  tool_calls_delta: number;
  tool_success_rate_delta: number;
  winner: string;
}

// ==================== Template Types ====================

export interface TemplateInfo {
  name: string;
  display_name: string;
  description: string;
  node_count: number;
  edge_count: number;
}

export interface TemplateDetail {
  name: string;
  display_name: string;
  description: string;
  canvas_data: import('./canvas').CanvasData;
}
