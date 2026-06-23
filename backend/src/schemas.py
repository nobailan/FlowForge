"""
FlowForge v0.1 - Pydantic 请求/响应模型
"""
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


# ==================== 画布节点 / 连线 ====================

class Position(BaseModel):
    x: float = 0
    y: float = 0


class CanvasNode(BaseModel):
    id: str
    type: str  # llm | tool | retriever | subagent | condition | loop
    config: dict[str, Any] = Field(default_factory=dict)
    position: Position = Field(default_factory=Position)
    label: str = ""


class CanvasEdge(BaseModel):
    source: str
    target: str
    label: str = ""  # 条件分支时使用 ("true", "false", ...)


class CanvasData(BaseModel):
    nodes: list[CanvasNode] = Field(default_factory=list)
    edges: list[CanvasEdge] = Field(default_factory=list)


# ==================== 架构 ====================

class ArchitectureCreate(BaseModel):
    name: str
    description: str = ""
    canvas_data: CanvasData


class ArchitectureUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    canvas_data: Optional[CanvasData] = None


class ArchitectureSummary(BaseModel):
    id: str
    name: str
    description: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ArchitectureDetail(ArchitectureSummary):
    canvas_data: CanvasData
    metadata: dict[str, Any] = Field(default_factory=dict)


# ==================== 执行 ====================

class ExecuteRequest(BaseModel):
    canvas_data: CanvasData
    input_text: str


class ExecuteResponse(BaseModel):
    execution_id: str
    status: str


class NodeEventOut(BaseModel):
    execution_id: str
    node_id: str
    node_type: str
    status: str  # pending | running | completed | error
    input_summary: str = ""
    output_summary: str = ""
    latency_ms: int = 0
    token_count: int = 0
    timestamp: float = 0


class ExecutionResult(BaseModel):
    id: str
    architecture_id: Optional[str] = None
    status: str
    input_data: dict[str, Any] = Field(default_factory=dict)
    output_data: dict[str, Any] = Field(default_factory=dict)
    total_latency_ms: int = 0
    total_tokens: int = 0
    node_events: list[dict[str, Any]] = Field(default_factory=list)
    error_message: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


# ==================== 评估 ====================

class EvaluateRequest(BaseModel):
    architecture_id: str
    testset_id: str


class EvalSummary(BaseModel):
    success_rate: float = 0
    avg_latency_ms: int = 0
    avg_tokens: int = 0
    total_cost_estimate: float = 0
    total_questions: int = 0
    passed: int = 0
    failed: int = 0
    # v0.2 Agent metrics
    total_tool_calls: int = 0
    total_tool_errors: int = 0
    tool_success_rate: float = 0
    avg_tool_calls_per_question: float = 0
    max_latency_ms: int = 0
    min_latency_ms: int = 0


class EvalDetail(BaseModel):
    test_id: int
    question: str
    category: str = ""
    success: bool
    latency_ms: int
    tokens: int
    output: str = ""
    error: str = ""
    # v0.2 Agent metrics
    tool_calls: int = 0
    tool_errors: int = 0
    tool_call_log: list[dict[str, Any]] = Field(default_factory=list)


class EvaluationResult(BaseModel):
    id: str
    architecture_id: str
    testset_name: str
    status: str
    summary: EvalSummary
    detail_results: list[EvalDetail] = Field(default_factory=list)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class CompareRequest(BaseModel):
    eval_run_ids: list[str]


class CompareResult(BaseModel):
    runs: list[EvaluationResult]
    diff: dict[str, Any] = Field(default_factory=dict)


# ==================== 测试集 ====================

class TestCase(BaseModel):
    model_config = {"extra": "allow"}  # 允许 expected_contains, notes 等额外字段
    id: int
    question: str
    category: str = ""
    expected_result_type: str = ""


class TestSetCreate(BaseModel):
    name: str
    description: str = ""
    test_cases: list[TestCase] = Field(default_factory=list)


class TestSetOut(BaseModel):
    id: str
    name: str
    description: str
    test_cases: list[dict[str, Any]] = Field(default_factory=list)
    created_at: Optional[str] = None


# ==================== 模板 ====================

class TemplateInfo(BaseModel):
    name: str
    display_name: str
    description: str
    node_count: int
    edge_count: int


class TemplateDetail(BaseModel):
    name: str
    display_name: str
    description: str
    canvas_data: CanvasData
