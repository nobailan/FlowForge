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
