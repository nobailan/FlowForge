"""
FlowForge v0.1 - Condition 节点
条件路由 —— 返回路由决策字符串。
"""
import time
from .base import register_node


@register_node(
    name="condition",
    display_name="Condition",
    description="根据条件判断走不同的分支路径",
    category="control",
    config_schema={
        "type": "object",
        "properties": {
            "field": {"type": "string", "title": "判断字段",
                      "description": "State 字段名或 node_id.output 引用上游输出"},
            "operator": {"type": "string", "title": "运算符",
                         "enum": ["equals", "contains", "not_empty", "gt", "lt", "is_true", "is_false"],
                         "default": "not_empty"},
            "value": {"type": "string", "title": "比较值", "default": ""},
        },
        "required": ["field", "operator"],
    },
    default_config={"field": "", "operator": "not_empty", "value": ""},
)
def condition_node_factory(node_id: str, config: dict):
    def route_fn(state: dict) -> str:
        start_time = time.time()
        field = config.get("field", "")
        operator = config.get("operator", "not_empty")
        expected = config.get("value", "")

        # Resolve field value — supports 3 formats:
        #   "node_id.output"  (new)      → node_outputs["node_id"]["output"]
        #   "node_id_output"  (old)      → node_outputs["node_id"]["output"]
        #   "field_name"      (top-level)→ state["field_name"]
        if ".output" in field:
            nid = field.replace(".output", "")
            field_val = str(state.get("node_outputs", {}).get(nid, {}).get("output", "")).strip()
        elif field.endswith("_output"):
            nid = field[: -len("_output")]
            field_val = str(state.get("node_outputs", {}).get(nid, {}).get("output", "")).strip()
        else:
            field_val = str(state.get(field, "")).strip()

        try:
            if operator == "not_empty": result = bool(field_val)
            elif operator == "is_true": result = str(field_val).lower() in ("true", "yes", "1")
            elif operator == "is_false": result = str(field_val).lower() in ("false", "no", "0")
            elif operator == "equals": result = str(field_val) == str(expected)
            elif operator == "contains": result = str(expected) in str(field_val)
            elif operator == "gt": result = float(field_val) > float(expected)
            elif operator == "lt": result = float(field_val) < float(expected)
            else: result = False
            route_decision = "true" if result else "false"
        except (ValueError, TypeError):
            route_decision = "false"

        elapsed_ms = int((time.time() - start_time) * 1000)

        if "node_outputs" not in state:
            state["node_outputs"] = {}
        state["node_outputs"][node_id] = {
            "output": route_decision, "tokens": 0,
            "latency_ms": elapsed_ms, "status": "completed", "node_type": "condition",
        }
        state["route_decision"] = route_decision
        state["node_timeline"].append({
            "node_id": node_id, "node_type": "condition", "status": "completed",
            "tokens": 0, "latency_ms": elapsed_ms,
            "input_preview": f"field={field}, op={operator}", "output_preview": route_decision,
        })
        return route_decision

    return route_fn
