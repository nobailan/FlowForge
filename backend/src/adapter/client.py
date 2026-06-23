"""
OpenCode HTTP API 客户端 — v0.2
直接构造 URL，不依赖 httpx query param 编码。
"""
import json
import httpx
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Optional


@dataclass
class SessionInfo:
    id: str
    title: str = ""
    agent: str = ""
    model: dict = field(default_factory=dict)
    tokens: dict = field(default_factory=dict)
    cost: float = 0.0
    raw: dict = field(default_factory=dict)


@dataclass
class PromptResult:
    message_id: str = ""
    text: str = ""
    tokens: dict = field(default_factory=dict)
    cost: float = 0.0
    finish: str = ""
    parts: list[dict] = field(default_factory=list)
    raw: dict = field(default_factory=dict)


class OpenCodeClient:

    def __init__(self, base_url: str = "http://localhost:4096"):
        self.base_url = base_url.rstrip("/")
        self._client: httpx.AsyncClient | None = None

    @property
    def http(self) -> httpx.AsyncClient:
        """懒加载 httpx client — 必须在 event loop 内首次访问。"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(600.0))
        return self._client

    def _url(self, path: str, directory: str) -> str:
        return f"{self.base_url}{path}?directory={directory}"

    async def create_session(self, directory: str, title: str = "",
                             agent: str = "build", model: Optional[dict] = None,
                             permission: Optional[list[dict]] = None) -> SessionInfo:
        body: dict[str, Any] = {}
        if title: body["title"] = title
        if agent: body["agent"] = agent
        if model:
            body["model"] = {"providerID": model.get("providerID", "anthropic"),
                             "id": model.get("modelID", "claude-sonnet-4-6")}
        if permission: body["permission"] = permission
        resp = await self.http.post(self._url("/session", directory), json=body)
        resp.raise_for_status()
        d = resp.json()
        return SessionInfo(id=d["id"], title=d.get("title", ""), agent=d.get("agent", ""),
                           model=d.get("model", {}), tokens=d.get("tokens", {}), raw=d)

    async def get_session(self, session_id: str, directory: str) -> SessionInfo:
        resp = await self.http.get(self._url(f"/session/{session_id}", directory))
        resp.raise_for_status()
        d = resp.json()
        return SessionInfo(id=d["id"], title=d.get("title", ""), agent=d.get("agent", ""),
                           model=d.get("model", {}), tokens=d.get("tokens", {}), raw=d)

    async def delete_session(self, session_id: str, directory: str) -> None:
        await self.http.delete(self._url(f"/session/{session_id}", directory))

    async def prompt(self, session_id: str, directory: str, parts: list[dict],
                     agent: str = "", model: Optional[dict] = None,
                     system: str = "") -> PromptResult:
        body: dict[str, Any] = {"parts": parts}
        if agent: body["agent"] = agent
        if model:
            body["model"] = {"providerID": model.get("providerID", "anthropic"),
                             "modelID": model.get("modelID", "claude-sonnet-4-6")}
        if system: body["system"] = system
        resp = await self.http.post(
            self._url(f"/session/{session_id}/message", directory), json=body)
        resp.raise_for_status()
        d = resp.json()
        text_parts = [p.get("text", "") for p in d.get("parts", []) if p.get("type") == "text"]
        info = d.get("info", {})
        return PromptResult(message_id=info.get("id", ""), text="\n".join(text_parts),
                            tokens=info.get("tokens", {}), cost=info.get("cost", 0),
                            finish=info.get("finish", ""), parts=d.get("parts", []), raw=d)

    async def list_providers(self, directory: str) -> dict:
        resp = await self.http.get(self._url("/provider", directory))
        resp.raise_for_status()
        return resp.json()

    async def close(self):
        await self.http.aclose()
