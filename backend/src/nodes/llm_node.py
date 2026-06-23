"""
FlowForge v0.2 - LLM 节点（Agent 模式）
通过 OpenCode Agent Session 执行，替代 v0.1 的单次 LLM API 调用。
"""
import time
import asyncio
from .base import register_node
from ..adapter import AgentNodeAdapter, WorkspaceManager

# 共享工作空间（MVP 使用项目根目录）
WORKSPACE = "E:/agentProject/harness_lab"

_adapter: AgentNodeAdapter | None = None
_workspace: WorkspaceManager | None = None


def _get_adapter() -> AgentNodeAdapter:
    global _adapter
    if _adapter is None:
        _adapter = AgentNodeAdapter("http://localhost:4096")
    return _adapter


def _get_workspace() -> WorkspaceManager:
    global _workspace
    if _workspace is None:
        _workspace = WorkspaceManager()
    return _workspace


@register_node(
    name="llm",
    display_name="LLM (Agent)",
    description="启动 OpenCode Agent 完成复杂任务。具备文件读写、Shell执行、搜索等全套工具。",
    category="llm",
    config_schema={
        "type": "object",
        "properties": {
            "opencode_agent": {
                "type": "string", "title": "OpenCode Agent",
                "enum": ["build", "plan", "general", "explore"],
                "default": "build",
            },
            "model_provider": {
                "type": "string", "title": "模型提供商",
                "default": "deepseek",
            },
            "model_id": {
                "type": "string", "title": "模型 ID",
                "default": "deepseek-v4-pro",
            },
            "system_prompt": {
                "type": "string", "title": "System Prompt",
                "default": "You are a helpful assistant. Complete the given task.",
            },
            "user_prompt_template": {
                "type": "string", "title": "任务模板",
                "default": "{{input}}",
                "description": "{{input}}=用户输入, {{node_id.output}}=上游节点输出",
            },
            "max_steps": {
                "type": "integer", "title": "最大步数",
                "default": 25, "minimum": 1, "maximum": 100,
            },
            "timeout_seconds": {
                "type": "integer", "title": "超时(秒)",
                "default": 300, "minimum": 10, "maximum": 1800,
            },
        },
        "required": [],
    },
    default_config={
        "opencode_agent": "build",
        "model_provider": "deepseek",
        "model_id": "deepseek-v4-pro",
        "system_prompt": "You are a helpful assistant. Complete the given task.",
        "user_prompt_template": "{{input}}",
        "max_steps": 25,
        "timeout_seconds": 300,
    },
)
def llm_node_factory(node_id: str, config: dict):
    """工厂函数：返回 LangGraph 兼容的节点函数。

    每个节点执行时：
    1. 创建 OpenCode Session
    2. 发送 prompt（含上游节点输出）
    3. 等待 Agent 完成
    4. 收集结果写入 state
    """

    def node_fn(state: dict) -> dict:
        start_time = time.time()

        user_prompt = config.get("user_prompt_template", "{{input}}")
        for key, value in state.items():
            if isinstance(value, (str, int, float, bool)):
                user_prompt = user_prompt.replace("{{" + key + "}}", str(value))
        node_outputs = state.get("node_outputs", {})
        for nid, ndata in node_outputs.items():
            if isinstance(ndata, dict):
                user_prompt = user_prompt.replace(
                    "{{" + nid + ".output}}", str(ndata.get("output", "")))

        upstream = {}
        for nid, ndata in node_outputs.items():
            if isinstance(ndata, dict) and ndata.get("output"):
                upstream[nid] = ndata["output"]

        try:
            adapter = AgentNodeAdapter("http://localhost:4096")
            execution_id = state.get("execution_id", "default")

            result = adapter.execute_sync(
                execution_id=execution_id,
                node_id=node_id,
                node_type="llm",
                node_config={
                    "opencode_agent": config.get("opencode_agent", "build"),
                    "model_config": {
                        "providerID": config.get("model_provider", "deepseek"),
                        "modelID": config.get("model_id", "deepseek-v4-pro"),
                    },
                    "system_prompt": config.get("system_prompt", ""),
                    "user_prompt_template": user_prompt,
                    "max_steps": config.get("max_steps", 25),
                    "timeout_seconds": config.get("timeout_seconds", 300),
                },
                input_text=user_prompt,
                upstream_outputs=upstream if upstream else None,
            )

        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            state.setdefault("node_outputs", {})[node_id] = {
                "output": f"[Agent Error] {str(e)}",
                "tokens": 0,
                "latency_ms": elapsed_ms,
                "status": "error",
                "node_type": "llm",
                "tool_calls": 0,
            }
            state["error"] = str(e)
            state["node_timeline"].append({
                "node_id": node_id, "node_type": "llm", "status": "error",
                "tokens": 0, "latency_ms": elapsed_ms,
                "output_preview": str(e)[:200],
            })
            return state

        # 写入结果
        state.setdefault("node_outputs", {})[node_id] = {
            "output": result.output,
            "tokens": result.tokens,
            "latency_ms": result.latency_ms,
            "status": result.status,
            "node_type": "llm",
            "tool_calls": result.tool_call_count,
            "streaming_events": result.streaming_events,
        }

        state["node_timeline"].append({
            "node_id": node_id, "node_type": "llm", "status": result.status,
            "tokens": result.tokens, "latency_ms": result.latency_ms,
            "input_preview": user_prompt[:200],
            "output_preview": result.output[:200],
        })
        state["total_tokens"] = state.get("total_tokens", 0) + result.tokens

        if result.status == "error":
            state["error"] = result.error

        return state

    return node_fn
