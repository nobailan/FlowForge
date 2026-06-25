"""
FlowForge v0.2 - Tool 节点（受限 Agent 模式）
仅允许 bash + read 工具，用于执行特定的工具操作。
"""
import time
import asyncio
from .base import register_node
from ..adapter import AgentNodeAdapter


_adapter: AgentNodeAdapter | None = None


def _get_adapter() -> AgentNodeAdapter:
    global _adapter
    if _adapter is None:
        _adapter = AgentNodeAdapter("http://localhost:4096")
    return _adapter


@register_node(
    name="tool",
    display_name="Tool (Agent)",
    description="受限 Agent，仅可使用 bash + read 工具执行指定操作。",
    category="tool",
    config_schema={
        "type": "object",
        "properties": {
            "tool_task": {
                "type": "string", "title": "工具任务描述",
                "default": "Execute the given task using available tools.",
            },
            "model_provider": {"type": "string", "title": "模型提供商", "default": "deepseek"},
            "model_id": {"type": "string", "title": "模型 ID", "default": "deepseek-v4-pro"},
            "timeout_seconds": {"type": "integer", "title": "超时(秒)", "default": 120},
        },
    },
    default_config={
        "tool_task": "Execute the given task using available tools.",
        "model_provider": "deepseek",
        "model_id": "deepseek-v4-pro",
        "timeout_seconds": 120,
    },
)
def tool_node_factory(node_id: str, config: dict):
    def node_fn(state: dict) -> dict:
        start_time = time.time()
        task = config.get("tool_task", "Execute the task.")
        input_text = state.get("input", "")

        # 展开模板变量 {{node_id.output}} 和 {{input}}
        node_outputs = state.get("node_outputs", {})
        for nid, ndata in node_outputs.items():
            if isinstance(ndata, dict):
                task = task.replace("{{" + nid + ".output}}", str(ndata.get("output", "")))
        task = task.replace("{{input}}", str(input_text))

        upstream = {}
        for nid, ndata in node_outputs.items():
            if isinstance(ndata, dict) and ndata.get("output"):
                upstream[nid] = ndata["output"]

        try:
            adapter = _get_adapter()
            result = adapter.execute_sync(
                execution_id=state.get("execution_id", "default"),
                node_id=node_id,
                node_type="tool",
                node_config={
                    "opencode_agent": "build",
                    "model_config": {
                        "providerID": config.get("model_provider", "deepseek"),
                        "modelID": config.get("model_id", "deepseek-v4-pro"),
                    },
                    "system_prompt": task,
                    "timeout_seconds": config.get("timeout_seconds", 120),
                    "max_steps": 10,
                    "allowed_tools": config.get("allowed_tools"),  # v0.5
                },
                input_text=input_text,
                upstream_outputs=upstream,
            )
        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            state.setdefault("node_outputs", {})[node_id] = {
                "output": f"[Tool Error] {e}", "tokens": 0,
                "latency_ms": elapsed_ms, "status": "error", "node_type": "tool",
            }
            return state

        state.setdefault("node_outputs", {})[node_id] = {
            "output": result.output, "tokens": result.tokens,
            "latency_ms": result.latency_ms, "status": result.status,
            "node_type": "tool",
        }
        state["total_tokens"] = result.tokens  # v0.5: delta, add reducer sums
        return state

    return node_fn
