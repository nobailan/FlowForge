"""
FlowForge v0.2 - Subagent 节点
"""
import time
import asyncio
from .base import register_node
from ..adapter import AgentNodeAdapter

@register_node(
    name="subagent", display_name="Subagent (Agent)",
    description="启动独立的子 Agent 完成指定子任务。",
    category="control",
    config_schema={
        "type": "object",
        "properties": {
            "agent_task": {"type": "string", "title": "子 Agent 任务",
                           "default": "You are a specialized sub-agent. Complete the assigned task thoroughly."},
            "model_provider": {"type": "string", "title": "模型提供商", "default": "deepseek"},
            "model_id": {"type": "string", "title": "模型 ID", "default": "deepseek-v4-pro"},
            "timeout_seconds": {"type": "integer", "title": "超时(秒)", "default": 300},
        },
    },
    default_config={"agent_task": "Complete the assigned task.", "model_provider": "deepseek",
                    "model_id": "deepseek-v4-pro", "timeout_seconds": 300},
)
def subagent_node_factory(node_id: str, config: dict):
    def node_fn(state: dict) -> dict:
        start_time = time.time()
        task = config.get("agent_task", "Complete the assigned task.")
        input_text = state.get("input", "")
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
            adapter = AgentNodeAdapter("http://localhost:4096")
            result = adapter.execute_sync(
                execution_id=state.get("execution_id", "default"), node_id=node_id,
                node_type="subagent",
                node_config={"opencode_agent": "general",
                             "model_config": {"providerID": config.get("model_provider", "deepseek"),
                                              "modelID": config.get("model_id", "deepseek-v4-pro")},
                             "system_prompt": task, "timeout_seconds": config.get("timeout_seconds", 300),
                             "max_steps": 20},
                input_text=input_text, upstream_outputs=upstream,
            )
        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            state.setdefault("node_outputs", {})[node_id] = {"output": f"[Subagent Error] {e}", "tokens": 0,
                                                              "latency_ms": elapsed_ms, "status": "error", "node_type": "subagent"}
            return state

        state.setdefault("node_outputs", {})[node_id] = {"output": result.output, "tokens": result.tokens,
                                                          "latency_ms": result.latency_ms, "status": result.status, "node_type": "subagent"}
        state["total_tokens"] = state.get("total_tokens", 0) + result.tokens
        return state
    return node_fn
