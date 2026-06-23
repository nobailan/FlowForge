// ==================== Canvas Data Types ====================

export interface Position {
  x: number;
  y: number;
}

export interface CanvasNodeData {
  id: string;
  type: string; // "llm" | "tool" | "retriever" | "subagent" | "condition" | "loop"
  label: string;
  config: Record<string, any>;
  position: Position;
  // Runtime data (populated during execution)
  _status?: "pending" | "running" | "completed" | "error";
  _output?: string;
  _tokens?: number;
  _latency_ms?: number;
}

export interface CanvasEdgeData {
  source: string;
  target: string;
  label: string; // For conditional branches: "true", "false", etc.
}

export interface CanvasData {
  nodes: CanvasNodeData[];
  edges: CanvasEdgeData[];
}

// ==================== Node Type Definition (from backend) ====================

export interface NodeTypeInfo {
  name: string;
  display_name: string;
  description: string;
  category: string;
  config_schema: Record<string, any>;
  default_config: Record<string, any>;
  input_ports: string[];
  output_ports: string[];
  icon: string;
}
