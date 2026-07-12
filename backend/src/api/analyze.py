"""
FlowForge v0.4 - 拓扑分析 + Prompt 生成 API
"""
from fastapi import APIRouter
from ..schemas import CanvasData
from ..engine.topology import analyze_topology
from ..engine.prompt_generator import generate_prompts

router = APIRouter()


@router.post("/topology")
def analyze_canvas(data: CanvasData):
    """分析画布拓扑结构。"""
    report = analyze_topology(data.model_dump())
    return {
        "pattern": report.pattern,
        "entry_nodes": report.entry_nodes,
        "terminal_nodes": report.terminal_nodes,
        "node_roles": report.node_roles,
        "is_valid": report.is_valid,
        "warnings": report.warnings,
        "suggestions": report.suggestions,
    }


@router.post("/prompts/generate")
def generate_node_prompts(data: dict):
    """为画布拓扑自动生成节点 Prompt。

    Body: { canvas_data, task_description }
    """
    canvas = data.get("canvas_data", {})
    task = data.get("task_description", "")
    result = generate_prompts(canvas, task)
    return {
        "topology": result.topology,
        "prompts": {
            nid: {
                "system_prompt": p.system_prompt,
                "user_prompt_template": p.user_prompt_template,
                "allowed_tools": p.allowed_tools,
                "output_schema": p.output_schema,
            }
            for nid, p in result.prompts.items()
        },
    }


@router.post("/eval/recommend")
def recommend_testset(data: dict):
    """根据画布拓扑推荐合适的测试集。

    Body: { canvas_data }
    Returns: { pattern, recommended_test_sets, reason }
    """
    from ..engine.topology import analyze_topology

    canvas = data.get("canvas_data", {})
    report = analyze_topology(canvas)

    # 模式 → 推荐测试集映射
    PATTERN_TEST_MAP = {
        "fan_out_fan_in": ["supervisor_worker", "parallel"],
        "sequential": ["sequential"],
        "conditional": ["conditional"],
        "cyclic": ["reflection_loop"],
        "mixed": ["general"],
    }

    recommended = PATTERN_TEST_MAP.get(report.pattern, ["general"])
    # 始终包含通用测试集
    if "general" not in recommended:
        recommended.insert(0, "general")

    reasons = {
        "fan_out_fan_in": "检测到 Dispatcher → Workers → Aggregator 结构，推荐 Supervisor-Worker 或 Parallel Experts 专用测试集",
        "sequential": "检测到流水线串行结构，推荐 Sequential Chain 专用测试集",
        "conditional": "检测到条件分支结构，推荐 Conditional Branch 专用测试集",
        "cyclic": "检测到循环反馈结构，推荐 Reflection Loop 专用测试集",
        "mixed": "检测到混合拓扑，推荐通用基础测试集",
    }

    return {
        "pattern": report.pattern,
        "node_roles": report.node_roles,
        "recommended_test_sets": recommended,
        "reason": reasons.get(report.pattern, "推荐通用测试集"),
    }
