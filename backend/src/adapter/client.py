"""
OpenCode HTTP API 客户端 — v0.4
使用 aiohttp（httpx 与 OpenCode 有 502 兼容问题）。
"""
import json as _json
import aiohttp
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class SessionInfo:
    id: str = ""
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
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=600)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    def _url(self, path: str, directory: str) -> str:
        return f"{self.base_url}{path}?directory={directory}"

    async def _post(self, url: str, body: dict) -> dict:
        s = await self._get_session()
        async with s.post(url, json=body) as resp:
            text = await resp.text()
            if resp.status >= 400:
                raise Exception(f"HTTP {resp.status}: {text[:200]}")
            return _json.loads(text) if text else {}

    async def _get(self, url: str) -> dict:
        s = await self._get_session()
        async with s.get(url) as resp:
            text = await resp.text()
            if resp.status >= 400:
                raise Exception(f"HTTP {resp.status}: {text[:200]}")
            return _json.loads(text) if text else {}

    async def _delete(self, url: str) -> None:
        s = await self._get_session()
        async with s.delete(url) as resp:
            if resp.status >= 400:
                text = await resp.text()
                raise Exception(f"HTTP {resp.status}: {text[:200]}")

    # ==================== Session ====================

    async def create_session(self, directory: str, title: str = "",
                             agent: str = "build", model: Optional[dict] = None,
                             permission: Optional[list[dict]] = None) -> SessionInfo:
        body: dict[str, Any] = {"title": title, "agent": agent}
        if model:
            body["model"] = {"providerID": model.get("providerID", "anthropic"),
                             "id": model.get("modelID", "claude-sonnet-4-6")}
        if permission:
            body["permission"] = permission
        d = await self._post(self._url("/session", directory), body)
        return SessionInfo(id=d["id"], title=d.get("title", ""), agent=d.get("agent", ""),
                           model=d.get("model", {}), tokens=d.get("tokens", {}), raw=d)

    async def get_session(self, session_id: str, directory: str) -> SessionInfo:
        d = await self._get(self._url(f"/session/{session_id}", directory))
        return SessionInfo(id=d["id"], title=d.get("title", ""), agent=d.get("agent", ""),
                           model=d.get("model", {}), tokens=d.get("tokens", {}), raw=d)

    async def delete_session(self, session_id: str, directory: str) -> None:
        await self._delete(self._url(f"/session/{session_id}", directory))

    # ==================== Prompt ====================

    async def prompt(self, session_id: str, directory: str, parts: list[dict],
                     agent: str = "", model: Optional[dict] = None,
                     system: str = "") -> PromptResult:
        body: dict[str, Any] = {"parts": parts}
        if agent: body["agent"] = agent
        if model:
            body["model"] = {"providerID": model.get("providerID", "anthropic"),
                             "modelID": model.get("modelID", "claude-sonnet-4-6")}
        if system: body["system"] = system
        d = await self._post(self._url(f"/session/{session_id}/message", directory), body)
        text_parts = [p.get("text", "") for p in d.get("parts", []) if p.get("type") == "text"]
        info = d.get("info", {})
        return PromptResult(message_id=info.get("id", ""), text="\n".join(text_parts),
                            tokens=info.get("tokens", {}), cost=info.get("cost", 0),
                            finish=info.get("finish", ""), parts=d.get("parts", []), raw=d)

    # ==================== Provider ====================

    async def list_providers(self, directory: str) -> dict:
        return await self._get(self._url("/provider", directory))

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
