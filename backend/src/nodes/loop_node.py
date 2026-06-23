"""
FlowForge v0.1 - Loop 节点
循环控制 —— 返回 "continue" 或 "exit" 路由决策。
"""
import time
from .base import register_node


@register_node(
    name="loop",
    display_name="Loop",
    description="循环控制节点，根据条件判断继续循环还是退出",
    category="control",
    config_schema={
        "type": "object",
        "properties": {
            "max_iterations": {"type": "integer", "title": "最大循环次数", "default": 5, "minimum": 1, "maximum": 50},
            "condition_field": {"type": "string", "title": "条件字段", "default": ""},
            "condition_operator": {"type": "string", "title": "条件运算符",
                                   "enum": ["contains", "not_contains", "not_empty", "equals"], "default": "contains"},
            "condition_value": {"type": "string", "title": "条件值", "default": "SATISFIED"},
        },
        "required": ["max_iterations"],
    },
    default_config={"max_iterations": 5, "condition_field": "",
                    "condition_operator": "contains", "condition_value": "SATISFIED"},
)
def loop_node_factory(node_id: str, config: dict):
    def route_fn(state: dict) -> str:
        start_time = time.time()
        max_iter = config.get("max_iterations", 5)
        condition_field = config.get("condition_field", "")
        condition_op = config.get("condition_operator", "contains")
        condition_val = config.get("condition_value", "")

        iter_key = f"{node_id}_iteration"
        current_iter = state.get(iter_key, 0) + 1
        state[iter_key] = current_iter

        try:
            if current_iter >= max_iter:
                route_decision = "exit"
            elif condition_field:
                field_val = str(state.get("node_outputs", {}).get(condition_field, {}).get("output", ""))
                if condition_op == "contains":
                    cond = condition_val in field_val if condition_val else bool(field_val)
                elif condition_op == "not_contains":
                    cond = condition_val not in field_val if condition_val else not field_val
                elif condition_op == "not_empty":
                    cond = bool(field_val)
                elif condition_op == "equals":
                    cond = field_val == condition_val
                else:
                    cond = False
                route_decision = "exit" if cond else "continue"
            else:
                route_decision = "continue"
        except (ValueError, TypeError):
            route_decision = "exit"

        elapsed_ms = int((time.time() - start_time) * 1000)

        if "node_outputs" not in state:
            state["node_outputs"] = {}
        state["node_outputs"][node_id] = {
            "output": route_decision, "tokens": 0,
            "latency_ms": elapsed_ms, "status": "completed", "node_type": "loop",
        }
        state["node_timeline"].append({
            "node_id": node_id, "node_type": "loop", "status": "completed",
            "tokens": 0, "latency_ms": elapsed_ms,
            "input_preview": f"iter={current_iter}/{max_iter}", "output_preview": route_decision,
        })
        return route_decision

    return route_fn
