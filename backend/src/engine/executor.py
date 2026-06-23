"""
FlowForge v0.1 - 执行引擎
运行编译后的图，收集执行结果。
"""
import asyncio
import time
import uuid

from .graph_builder import GraphBuilder, GraphBuildError
from .monitor import EventBus, NodeEvent, ws_manager
from .state import create_initial_state


class FlowExecutor:
    """编排一次完整的流程执行。"""

    def __init__(self, canvas_data: dict, execution_id: str | None = None):
        self.canvas = canvas_data
        self.execution_id = execution_id or str(uuid.uuid4())
        self.event_bus = EventBus(self.execution_id)

    async def execute(self, user_input: str) -> dict:
        start_time = time.time()

        # 构建图（监控包装器在 GraphBuilder 内部，执行时收集事件到 event_bus._events）
        builder = GraphBuilder(self.canvas, event_bus=self.event_bus)
        try:
            graph = builder.build()
        except GraphBuildError as e:
            return self._error_result(f"Graph build failed: {e}")

        agent = graph.compile()
        initial_state = create_initial_state(user_input)
        config = {"configurable": {"thread_id": self.execution_id}}

        # 立即广播所有节点为 "running"——前端不再显示 waiting
        from .monitor import NodeEvent
        for node in self.canvas.get("nodes", []):
            ev = NodeEvent(
                execution_id=self.execution_id,
                node_id=node["id"],
                node_type=node.get("type", "unknown"),
                status="running",
                timestamp=time.time(),
            )
            self.event_bus._events.append(ev)
            await ws_manager.broadcast(self.execution_id, ev)

        # 在线程中执行 LangGraph（阻塞式 LLM 调用）
        try:
            result_state = await asyncio.to_thread(
                agent.invoke, initial_state, config
            )
        except Exception as e:
            return self._error_result(f"Execution failed: {e}")

        # 执行完成后，把收集到的所有事件广播出去
        for event in self.event_bus._events:
            await ws_manager.broadcast(self.execution_id, event)

        # 为每个 Agent 节点生成完成事件并存入 event_bus
        node_outputs = result_state.get("node_outputs", {})
        from .monitor import NodeEvent
        for nid, ndata in node_outputs.items():
            if isinstance(ndata, dict):
                ev = NodeEvent(
                    execution_id=self.execution_id,
                    node_id=nid,
                    node_type=ndata.get("node_type", "unknown"),
                    status=ndata.get("status", "completed"),
                    token_count=ndata.get("tokens", 0),
                    latency_ms=ndata.get("latency_ms", 0),
                    output_summary=str(ndata.get("output", ""))[:200],
                )
                self.event_bus._events.append(ev)
                await ws_manager.broadcast(self.execution_id, ev)

        total_elapsed = int((time.time() - start_time) * 1000)

        # 确定最终输出
        final_output = result_state.get("final_output", "")
        if not final_output:
            for node in reversed(self.canvas.get("nodes", [])):
                nid = node["id"]
                ndata = node_outputs.get(nid, {})
                output = ndata.get("output", "")
                if output:
                    final_output = output
                    break

        # 聚合工具调用指标
        total_tool_calls = 0
        for ndata in node_outputs.values():
            if isinstance(ndata, dict):
                total_tool_calls += ndata.get("tool_calls", 0)

        return {
            "execution_id": self.execution_id,
            "status": "completed",
            "final_output": final_output,
            "total_tokens": result_state.get("total_tokens", 0),
            "total_latency_ms": total_elapsed,
            "node_timeline": result_state.get("node_timeline", []),
            "all_events": self.event_bus.get_all_events(),
            "error": result_state.get("error", ""),
            "total_tool_calls": total_tool_calls,
            "node_outputs": node_outputs,
        }

    def _error_result(self, message: str) -> dict:
        return {
            "execution_id": self.execution_id,
            "status": "failed",
            "final_output": "",
            "total_tokens": 0,
            "total_latency_ms": 0,
            "node_timeline": [],
            "all_events": [],
            "error": message,
            "total_tool_calls": 0,
            "node_outputs": {},
        }
