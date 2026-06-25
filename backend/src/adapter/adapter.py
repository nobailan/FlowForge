"""
AgentNodeAdapter — 将 FlowForge 节点映射为 OpenCode Agent Session。
v0.2 核心模块，替代 v0.1 中单次 LLM API 调用的节点实现。
"""
import time
import asyncio
import queue
from dataclasses import dataclass, field
from typing import Any, Optional

from .client import OpenCodeClient, SessionInfo, PromptResult
from .sandbox import WorkspaceManager
from .monitor_bridge import MonitorBridge
from ..engine.monitor import ws_manager


@dataclass
class NodeResult:
    """节点执行结果。"""
    node_id: str = ""
    output: str = ""
    tokens: int = 0
    latency_ms: int = 0
    status: str = "completed"  # completed | error
    error: str = ""
    tool_call_count: int = 0
    tool_call_log: list[dict] = field(default_factory=list)
    streaming_events: list[dict] = field(default_factory=list)
    raw: dict = field(default_factory=dict)


# 节点类型 → OpenCode Agent 映射
NODE_AGENT_MAP = {
    "llm": "build",         # 通用 Agent，全部工具
    "tool": "build",        # 受限 Agent（通过 permission 限制工具）
    "retriever": "build",   # 检索 Agent（仅 glob+grep+read）
    "subagent": "general",  # 子 Agent
}

# 节点类型 → 工具权限白名单
NODE_TOOLS_MAP = {
    "llm": None,            # None = 全部工具
    "tool": ["bash", "read"],
    "retriever": ["glob", "grep", "read"],
    "subagent": None,
    "condition": None,
    "loop": None,
}


class AgentNodeAdapter:
    """将 FlowForge 节点执行委托给 OpenCode Agent Session。

    用法:
        adapter = AgentNodeAdapter("http://localhost:4096")
        result = await adapter.execute(
            execution_id="run_001",
            node_id="supervisor",
            node_type="llm",
            node_config={"model": {...}, "system_prompt": "...", "max_steps": 25},
            input_text="用户问题...",
            upstream_outputs={"node_a": "...", "node_b": "..."}
        )
    """

    def __init__(self, opencode_url: str = "http://localhost:4096"):
        self.client = OpenCodeClient(opencode_url)
        self.workspace = WorkspaceManager()

    def execute_sync(self, *args, **kwargs) -> NodeResult:
        """同步执行——用于 LangGraph 节点中（无 event loop 冲突）。"""
        import threading, queue
        result_queue: queue.Queue = queue.Queue()
        def _run():
            result_queue.put(asyncio.run(self.execute(*args, **kwargs)))
        t = threading.Thread(target=_run)
        t.start()
        t.join()
        return result_queue.get()

    async def execute(
        self,
        execution_id: str,
        node_id: str,
        node_type: str,
        node_config: dict,
        input_text: str,
        upstream_outputs: Optional[dict[str, str]] = None,
    ) -> NodeResult:
        """执行一个节点，返回结构化结果。"""
        start_time = time.time()

        # MVP: 使用项目根目录作为 workspace（temp 目录 OpenCode 不接受）
        directory = "E:/agentProject/harness_lab"

        # 2. 解析配置
        agent = node_config.get("opencode_agent") or NODE_AGENT_MAP.get(node_type, "build")
        model = node_config.get("model_config") or {"providerID": "anthropic", "modelID": "claude-sonnet-4-6"}
        max_steps = node_config.get("max_steps", 25)
        timeout = node_config.get("timeout_seconds", 300)
        # v0.5: 优先使用 config 中的 allowed_tools（由 AutoPrompt 动态分配），否则回退到静态映射
        # 注意：[] 表示"不允许任何工具"，不能用 `or`（[] 是 falsy）
        cfg_tools = node_config.get("allowed_tools")
        if cfg_tools is not None:
            tools = cfg_tools
        else:
            tools = NODE_TOOLS_MAP.get(node_type)
        system_prompt = node_config.get("system_prompt", "")

        # 3. 构建 prompt（v0.5: 传入 execution_id 用于 REF 解析）
        parts = self._build_prompt(input_text, upstream_outputs, node_config, execution_id)
        permission = self._build_permission(tools)

        try:
            # 4. 创建 Session
            session = await self.client.create_session(
                directory=directory,
                title=f"{execution_id}/{node_id}",
                agent=agent,
                model=model,
                permission=permission,
            )

            # 5. SSE 监控: bridge 线程后台收集事件
            bridge = MonitorBridge(execution_id, node_id, directory, self.client.base_url)
            bridge.start()

            # 6. 发送 prompt（同步等待）
            result = await asyncio.wait_for(
                self.client.prompt(
                    session_id=session.id,
                    directory=directory,
                    parts=parts,
                    system=system_prompt,
                ),
                timeout=timeout,
            )

            # 7. 停止 bridge，flush 全部事件到 WebSocket（历史回放）
            bridge.stop()
            events = bridge.get_events()
            for ev in events:
                await ws_manager.broadcast_streaming(execution_id, ev)

            elapsed_ms = int((time.time() - start_time) * 1000)
            tokens = (
                result.tokens.get("input", 0)
                + result.tokens.get("output", 0)
                + result.tokens.get("reasoning", 0)
            )
            tool_count = sum(
                1 for p in result.parts
                if p.get("type") in ("tool_call", "tool_result")
            )

            # 8. 清理 Session + HTTP client
            try:
                await self.client.delete_session(session.id, directory)
            except Exception:
                pass
            await self.client.close()

            return NodeResult(
                node_id=node_id,
                output=result.text,
                tokens=tokens,
                latency_ms=elapsed_ms,
                status="completed",
                tool_call_count=tool_count,
                tool_call_log=[
                    p for p in result.parts
                    if p.get("type") in ("tool_call", "tool_result")
                ],
                streaming_events=bridge.get_events(),
                raw=result.raw,
            )

        except asyncio.TimeoutError:
            elapsed_ms = int((time.time() - start_time) * 1000)
            return NodeResult(node_id=node_id, status="error",
                              error=f"Timeout after {timeout}s", latency_ms=elapsed_ms)
        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            return NodeResult(node_id=node_id, status="error",
                              error=str(e), latency_ms=elapsed_ms)

    async def cleanup_execution(self, execution_id: str) -> None:
        """清理一次执行的所有工作目录。"""
        self.workspace.cleanup(execution_id)

    def _build_prompt(
        self,
        input_text: str,
        upstream_outputs: Optional[dict[str, str]],
        config: dict,
        execution_id: str = "",
    ) -> list[dict]:
        """根据节点类型构建发给 Agent 的 prompt parts。

        v0.5: 解析上游输出中的 [REF: artifact://...] 引用，按需获取内容。
        """
        from ..engine.artifact_store import get_artifact_store

        parts: list[dict] = []

        # 上游输出作为上下文（解析 REF 引用）
        if upstream_outputs:
            store = get_artifact_store()
            context_lines = ["## Upstream Node Outputs"]
            for name, output in upstream_outputs.items():
                # v0.5: 按需解析 REF，避免直接塞入大段内容
                # 如果输出短（<500 chars），直接包含；如果长，只包含摘要 + REF
                if len(output) > 500:
                    # 尝试提取 JSON 中的 result 字段
                    try:
                        import json as _json
                        parsed = _json.loads(output)
                        summary = parsed.get("result", parsed.get("answer", output[:200]))
                    except Exception:
                        summary = output[:200]
                    context_lines.append(
                        f"\n### {name}\n{summary}...\n[Full output in execution log]"
                    )
                else:
                    # v0.5: 解析输出中的 REF 引用
                    resolved = store.resolve_refs(output)
                    context_lines.append(f"\n### {name}\n{resolved}")
            context = "\n".join(context_lines)
            parts.append({"type": "text", "text": context})

        # 用户输入 / 任务描述
        task = input_text
        user_prompt_template = config.get("user_prompt_template", "")
        if user_prompt_template and user_prompt_template != "{{input}}":
            task = user_prompt_template
            if upstream_outputs:
                for name, output in upstream_outputs.items():
                    task = task.replace(f"{{{{{name}.output}}}}", output)
            task = task.replace("{{input}}", input_text)

        parts.append({"type": "text", "text": f"## Task\n{task}"})
        return parts

    def _build_permission(self, tools: Optional[list[str]]) -> list[dict]:
        """构建工具权限列表。"""
        if tools is None:
            return []  # 空列表 = 全部允许
        return [
            {"permission": tool, "action": "allow", "pattern": "*"}
            for tool in tools
        ]


# 模块级单例（复用 HTTP 连接）
_adapter: Optional[AgentNodeAdapter] = None


def get_adapter(opencode_url: str = "http://localhost:4096") -> AgentNodeAdapter:
    global _adapter
    if _adapter is None:
        _adapter = AgentNodeAdapter(opencode_url)
    return _adapter
