"""
FlowForge v0.6 - 实时监控桥接
MonitorBridge 线程监听 OpenCode SSE → 写入全局 queue.Queue
→ execute.py 的 stream_pusher 协程（FastAPI event loop）轮询推送 WebSocket。

解决了 v0.4-v0.5 的跨 event loop 问题：
之前 BridgePoller 在自己的 asyncio.run() 里直接调 ws_manager →
WebSocket 绑在 FastAPI 的 event loop → 跨 loop 操作失败。
现在改为：MonitorBridge 只负责写入全局队列，推送由 FastAPI 侧完成。
"""
import time
import json
import threading
import queue

# ============================================================
# v0.6: 全局事件队列（跨线程桥梁）
# ============================================================

# 模块级全局队列，MonitorBridge 线程写入，FastAPI 协程读出
_stream_queue: queue.Queue = queue.Queue()

# 按 execution_id 索引的活跃队列引用，用于 cleanup
_active_queues: dict[str, list[queue.Queue]] = {}


def get_stream_queue() -> queue.Queue:
    """获取全局流式事件队列。"""
    return _stream_queue


def register_execution(execution_id: str):
    """注册一次执行（用于后续 cleanup）。"""
    _active_queues[execution_id] = []


def unregister_execution(execution_id: str):
    """清理一次执行的所有队列引用。"""
    _active_queues.pop(execution_id, None)


# ============================================================
# v0.6 标准化事件类型
# ============================================================

EVENT_NODE_START = "node:start"
EVENT_NODE_THINKING = "node:thinking"
EVENT_NODE_TOOL = "node:tool"
EVENT_NODE_TOOL_RESULT = "node:tool_result"
EVENT_NODE_END = "node:end"


def make_event(event_type: str, execution_id: str, node_id: str, **kwargs) -> dict:
    """构造标准化事件。"""
    ev = {
        "event": event_type,
        "execution_id": execution_id,
        "node_id": node_id,
        "timestamp": time.time(),
    }
    ev.update(kwargs)
    return ev


# ============================================================
# MonitorBridge
# ============================================================

class MonitorBridge:
    """OpenCode SSE 监听器（独立线程）。

    连接到 OpenCode 的 /event SSE 端点，解析事件，
    写入全局 _stream_queue（供 FastAPI 协程实时推送）。
    """

    def __init__(self, execution_id: str, node_id: str, directory: str,
                 opencode_url: str = "http://localhost:4096"):
        self.execution_id = execution_id
        self.node_id = node_id
        self.directory = directory
        self.opencode_url = opencode_url
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._events: list[dict] = []    # 本地备份（用于历史回放）
        self._last_text = ""

    def start(self):
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)

    def get_events(self) -> list[dict]:
        """获取本地收集的所有事件（历史回放用）。"""
        return self._events

    def _run(self):
        import urllib.request
        import ssl

        url = f"{self.opencode_url}/event?directory={self.directory}"
        ctx = ssl.create_default_context()

        try:
            req = urllib.request.Request(url, headers={"Accept": "text/event-stream"})
            resp = urllib.request.urlopen(req, context=ctx, timeout=5)

            buf = ""
            while not self._stop.is_set():
                try:
                    chunk = resp.read(4096)
                    if not chunk:
                        break
                    text = chunk.decode("utf-8", errors="replace")
                    buf += text
                    while "\n\n" in buf:
                        frame, buf = buf.split("\n\n", 1)
                        self._process_frame(frame)
                except Exception:
                    break
        except Exception:
            pass

    def _process_frame(self, event_str: str):
        for line in event_str.split("\n"):
            if not line.startswith("data: "):
                continue
            try:
                data = json.loads(line[6:])
                event_type = data.get("type", "")
                props = data.get("properties", {})

                if event_type == "message.part.updated":
                    part = props.get("part", {})
                    if part.get("type") == "text":
                        text = part.get("text", "")
                        if not text or not text.strip():
                            continue  # 跳过空文本和纯空白
                        self._last_text += text
                        ev = make_event(
                            EVENT_NODE_THINKING,
                            self.execution_id, self.node_id,
                            text=text,
                        )
                    elif part.get("type") == "tool_call":
                        ev = make_event(
                            EVENT_NODE_TOOL,
                            self.execution_id, self.node_id,
                            tool_name=part.get("tool", "?"),
                            tool_input=str(part.get("input", ""))[:200],
                        )
                    else:
                        continue
                elif event_type == "session.status":
                    status = props.get("status", {})
                    if status.get("type") == "idle":
                        ev = make_event(
                            EVENT_NODE_TOOL_RESULT,
                            self.execution_id, self.node_id,
                            tool_name="",
                            summary="idle",
                        )
                    else:
                        continue
                else:
                    continue

                # 写入本地备份
                self._events.append(ev)
                # v0.6: 写入全局队列，供 FastAPI 协程实时推送
                _stream_queue.put(ev)

            except Exception:
                pass


# ============================================================
# 工具函数：合并相邻 thinking 事件
# ============================================================

def merge_thinking(events: list[dict]) -> list[dict]:
    """合并连续 thinking 事件，减少推送量。"""
    if len(events) <= 1:
        return events
    result = []
    buf = None
    for ev in events:
        if ev.get("event") == EVENT_NODE_THINKING:
            if buf is None:
                buf = dict(ev)
            else:
                buf["text"] = (buf.get("text", "") or "") + (ev.get("text", "") or "")
                buf["timestamp"] = ev["timestamp"]
        else:
            if buf is not None:
                result.append(buf)
                buf = None
            result.append(ev)
    if buf is not None:
        result.append(buf)
    return result
