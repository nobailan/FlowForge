"""
FlowForge v0.4 - SSE 监控桥接（实时流式版）
MonitorBridge 线程监听 SSE → queue → BridgePoller 线程实时推送。
"""
import time
import json
import threading
import queue
from ..engine.monitor import ws_manager


class MonitorBridge:
    """OpenCode SSE 监听器（独立线程）。

    将 SSE 事件解析后同时放入 _events list 和 _queue（用于实时推送）。
    """

    def __init__(self, execution_id: str, node_id: str, directory: str,
                 opencode_url: str = "http://localhost:4096"):
        self.execution_id = execution_id
        self.node_id = node_id
        self.directory = directory
        self.opencode_url = opencode_url
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._events: list[dict] = []
        self._queue: queue.Queue = queue.Queue()
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
        return self._events

    def get_queue(self) -> queue.Queue:
        return self._queue

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

                ev = {
                    "execution_id": self.execution_id,
                    "node_id": self.node_id,
                    "event_type": "thinking",
                    "text": "",
                    "tool_name": "",
                    "tool_input": "",
                    "timestamp": time.time(),
                }

                if event_type == "message.part.updated":
                    part = props.get("part", {})
                    if part.get("type") == "text":
                        text = part.get("text", "")
                        self._last_text += text
                        ev["text"] = text
                        ev["event_type"] = "thinking"
                    elif part.get("type") == "tool_call":
                        ev["event_type"] = "tool_start"
                        ev["tool_name"] = part.get("tool", "?")
                        ev["tool_input"] = str(part.get("input", ""))[:200]
                    else:
                        continue
                elif event_type == "session.status":
                    status = props.get("status", {})
                    if status.get("type") == "idle":
                        ev["event_type"] = "tool_end"
                    else:
                        continue
                else:
                    continue

                self._events.append(ev)
                self._queue.put(ev)  # 实时推入队列

            except Exception:
                pass


class BridgePoller:
    """轮询 MonitorBridge 队列，实时推送事件到 WebSocket。

    在独立线程中运行自己的 asyncio loop，
    每 200ms 轮询 queue，合并相邻 thinking，通过 ws_manager 推送。
    """

    def __init__(self, bridge: MonitorBridge):
        self._bridge = bridge
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def start(self):
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)

    def _run(self):
        """在新线程中创建独立 asyncio loop，轮询 queue 并推送。"""
        import asyncio

        async def poll_loop():
            q = self._bridge.get_queue()
            exec_id = self._bridge.execution_id
            pending_events: list[dict] = []
            last_flush = time.time()

            while not self._stop.is_set():
                # 收集队列中所有事件
                try:
                    while True:
                        ev = q.get_nowait()
                        pending_events.append(ev)
                except queue.Empty:
                    pass

                # 每 200ms 或累积 > 5 个事件时 flush
                now = time.time()
                if pending_events and (now - last_flush > 0.2 or len(pending_events) > 5):
                    # 合并相邻 thinking
                    merged = _merge_thinking(pending_events)
                    for ev in merged:
                        await ws_manager.broadcast_streaming(exec_id, ev)
                    pending_events.clear()
                    last_flush = now

                await asyncio.sleep(0.1)

            # 最后 flush 剩余事件
            if pending_events:
                for ev in _merge_thinking(pending_events):
                    await ws_manager.broadcast_streaming(exec_id, ev)

        asyncio.run(poll_loop())


def _merge_thinking(events: list[dict]) -> list[dict]:
    """合并连续 thinking 事件，减少推送量。"""
    if len(events) <= 1:
        return events
    result = []
    buf = None
    for ev in events:
        if ev["event_type"] == "thinking":
            if buf is None:
                buf = dict(ev)
            else:
                buf["text"] += ev["text"]
                buf["timestamp"] = ev["timestamp"]
        else:
            if buf is not None:
                result.append(buf)
                buf = None
            result.append(ev)
    if buf is not None:
        result.append(buf)
    return result
