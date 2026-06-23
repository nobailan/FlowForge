"""
FlowForge v0.1 - 实时监控
EventBus（发布/订阅）+ WebSocketManager（连接管理 + 事件回放）。
"""
import asyncio
import time
from dataclasses import dataclass, asdict
from typing import Callable, Awaitable, Any
from fastapi import WebSocket


@dataclass
class NodeEvent:
    """节点执行事件。"""
    execution_id: str
    node_id: str
    node_type: str
    status: str            # pending | running | completed | error
    input_summary: str = ""
    output_summary: str = ""
    latency_ms: int = 0
    token_count: int = 0
    timestamp: float = 0.0


class EventBus:
    """单次执行的事件总线（内存 pub/sub）。"""

    def __init__(self, execution_id: str):
        self.execution_id = execution_id
        self._subscribers: list[Callable[[NodeEvent], Awaitable[None]]] = []
        self._events: list[NodeEvent] = []

    def subscribe(self, callback: Callable[[NodeEvent], Awaitable[None]]):
        self._subscribers.append(callback)

    def subscribe_sync(self, callback: Callable[[NodeEvent], None]):
        async def wrapper(event: NodeEvent):
            callback(event)
        self._subscribers.append(wrapper)

    async def emit(self, event: NodeEvent):
        event.timestamp = time.time()
        self._events.append(event)
        for cb in self._subscribers:
            try:
                await cb(event)
            except Exception:
                pass

    def emit_sync(self, event: NodeEvent):
        event.timestamp = time.time()
        self._events.append(event)
        for cb in self._subscribers:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(cb(event))
            except Exception:
                pass

    def get_all_events(self) -> list[dict]:
        return [asdict(e) for e in self._events]


class WebSocketManager:
    """WebSocket 连接管理 + 事件历史回放。

    新客户端连接时，自动回放该 execution 已发生的事件。
    """

    _instance: "WebSocketManager | None" = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._connections: dict[str, list[WebSocket]] = {}
            cls._instance._history: dict[str, list[dict]] = {}
            cls._instance._streaming_history: dict[str, list[dict]] = {}
        return cls._instance

    async def connect(self, execution_id: str, websocket: WebSocket):
        """注册 WebSocket，并回放已有事件。"""
        if execution_id not in self._connections:
            self._connections[execution_id] = []
        self._connections[execution_id].append(websocket)

        # 回放历史事件
        for event_dict in self._history.get(execution_id, []):
            try:
                await websocket.send_json({"type": "node_event", "data": event_dict})
            except Exception:
                pass
        # 回放流式事件
        for ev_dict in self._streaming_history.get(execution_id, []):
            try:
                await websocket.send_json({"type": "streaming_event", "data": ev_dict})
            except Exception:
                pass

    async def disconnect(self, execution_id: str, websocket: WebSocket):
        conns = self._connections.get(execution_id, [])
        if websocket in conns:
            conns.remove(websocket)

    async def broadcast(self, execution_id: str, event: NodeEvent):
        """广播节点状态事件并存入历史。"""
        event_dict = asdict(event)
        if execution_id not in self._history:
            self._history[execution_id] = []
        self._history[execution_id].append(event_dict)

        dead: list[WebSocket] = []
        for ws in self._connections.get(execution_id, []):
            try:
                await ws.send_json({"type": "node_event", "data": event_dict})
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(execution_id, ws)

    async def broadcast_streaming(self, execution_id: str, event_dict: dict):
        """广播流式事件（thinking/tool_start/tool_end）并存入历史。"""
        if execution_id not in self._streaming_history:
            self._streaming_history[execution_id] = []
        self._streaming_history[execution_id].append(event_dict)

        dead: list[WebSocket] = []
        for ws in self._connections.get(execution_id, []):
            try:
                await ws.send_json({"type": "streaming_event", "data": event_dict})
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(execution_id, ws)

    def get_history(self, execution_id: str) -> list[dict]:
        return self._history.get(execution_id, [])

    def clear_history(self, execution_id: str):
        self._history.pop(execution_id, None)
        self._streaming_history.pop(execution_id, None)

    def get_connection_count(self, execution_id: str) -> int:
        return len(self._connections.get(execution_id, []))


ws_manager = WebSocketManager()
