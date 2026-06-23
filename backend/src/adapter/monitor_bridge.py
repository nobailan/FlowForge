"""
FlowForge v0.3 - SSE 监控桥接（线程版）
在独立线程中监听 OpenCode SSE，避免和主 event loop 死锁。
"""
import time
import json
import threading
import queue
from ..engine.monitor import ws_manager


class MonitorBridge:
    """桥接 OpenCode SSE → FlowForge WebSocket（线程版）。

    在独立线程中运行 SSE 监听，通过线程安全队列传递事件。
    主线程轮询队列并通过 ws_manager 推送到前端。
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
        self._last_text = ""

    def start(self):
        """启动后台线程监听 SSE。"""
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        """停止监听。"""
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)

    def get_events(self) -> list[dict]:
        return self._events

    def get_last_text(self) -> str:
        return self._last_text

    def _run(self):
        """后台线程：使用同步 HTTP 客户端监听 SSE。"""
        import urllib.request
        import ssl

        url = f"{self.opencode_url}/event?directory={self.directory}"
        ctx = ssl.create_default_context()

        try:
            req = urllib.request.Request(url, headers={"Accept": "text/event-stream"})
            resp = urllib.request.urlopen(req, context=ctx, timeout=5)

            buffer = ""
            while not self._stop.is_set():
                try:
                    chunk = resp.read(4096)
                    if not chunk:
                        break
                    text = chunk.decode("utf-8", errors="replace")
                    buffer += text
                    while "\n\n" in buffer:
                        event_str, buffer = buffer.split("\n\n", 1)
                        self._process_frame(event_str)
                except Exception:
                    break
        except Exception:
            pass

    def _process_frame(self, event_str: str):
        """解析单个 SSE 事件帧。"""
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
                        self._events.append(ev)

                    elif part.get("type") == "tool_call":
                        ev["event_type"] = "tool_start"
                        ev["tool_name"] = part.get("tool", "?")
                        ev["tool_input"] = str(part.get("input", ""))[:200]
                        self._events.append(ev)

                elif event_type == "session.status":
                    status = props.get("status", {})
                    if status.get("type") == "idle":
                        ev["event_type"] = "tool_end"
                        self._events.append(ev)

            except Exception:
                pass
