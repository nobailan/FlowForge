"""
FlowForge v0.1 - 模板 API
"""
from fastapi import APIRouter, HTTPException

from ..schemas import TemplateInfo, TemplateDetail, CanvasData
from ..engine.templates import list_templates, get_template

router = APIRouter()


@router.get("/", response_model=list[TemplateInfo])
def list_all_templates():
    """列出所有内置模板。"""
    return [TemplateInfo(**t) for t in list_templates()]


@router.get("/node-types")
def list_node_types():
    """列出所有可用的节点类型（供前端画布面板使用）。"""
    from ..engine.registry import get_registry
    registry = get_registry()
    types = registry.list_all()
    return [
        {
            "name": t.name,
            "display_name": t.display_name,
            "description": t.description,
            "category": t.category,
            "config_schema": t.config_schema,
            "default_config": t.default_config,
            "input_ports": t.input_ports,
            "output_ports": t.output_ports,
            "icon": t.icon,
        }
        for t in types
    ]


@router.get("/{template_name}", response_model=TemplateDetail)
def get_template_detail(template_name: str):
    """获取指定模板的完整 canvas JSON。"""
    template = get_template(template_name)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template '{template_name}' not found")

    return TemplateDetail(
        name=template["name"],
        display_name=template["display_name"],
        description=template["description"],
        canvas_data=CanvasData(**template["canvas_data"]),
    )
