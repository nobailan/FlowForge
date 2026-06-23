// ==================== Execution Types ====================

export interface NodeEvent {
  execution_id: string;
  node_id: string;
  node_type: string;
  status: "pending" | "running" | "completed" | "error";
  input_summary: string;
  output_summary: string;
  latency_ms: number;
  token_count: number;
  timestamp: number;
}

export interface ExecutionResult {
  id: string;
  architecture_id?: string;
  status: string;
  input_data: Record<string, any>;
  output_data: Record<string, any>;
  total_latency_ms: number;
  total_tokens: number;
  node_events: NodeEvent[];
  error_message: string;
  started_at?: string;
  completed_at?: string;
}

export interface ExecuteResponse {
  execution_id: string;
  status: string;
}
