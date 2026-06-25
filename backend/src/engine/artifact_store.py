"""
FlowForge v0.5 - 工件存储（Artifact Store）
第一刀：Agent 之间传引用不传内容。

基于 Redis，存储执行过程中产生的文件内容。
Agent 通过 [REF: artifact://key] 语法引用，无需将文件内容塞入上下文。
"""
import json
import time
import hashlib
from dataclasses import dataclass, field
from typing import Optional

import redis


@dataclass
class Artifact:
    """存储的工件。"""
    key: str                    # artifact:{exec_id}:{node_id}:{filename}:v{version}
    file_path: str              # 原始文件绝对路径
    content: str                # 完整内容（只在 Store 里存一份）
    line_count: int
    metadata: dict = field(default_factory=dict)   # {mtime, size, encoding, checksum}
    created_by: str = ""        # node_id
    created_at: float = 0.0     # timestamp
    ttl: int = 600              # 默认 10 分钟过期


class ArtifactStore:
    """Redis 工件存储。

    用法:
        store = ArtifactStore()
        key = store.put("exec_001", "node_a", "/path/to/config.py", content)
        art = store.get(key)
        snippet = store.get_range(key, 10, 50)

        # 解析 Agent 输出中的引用
        resolved = store.resolve_refs(agent_output)
    """

    REF_PATTERN = "[REF: artifact://"

    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0,
                 default_ttl: int = 600):
        self.redis = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        self.default_ttl = default_ttl
        self._verify_connection()

    def _verify_connection(self):
        try:
            self.redis.ping()
        except redis.ConnectionError as e:
            print(f"[ArtifactStore] WARNING: Redis not available ({e}). "
                  f"Falling back to in-memory store.")
            self._fallback: dict[str, Artifact] = {}
            self._use_fallback = True
            return
        self._use_fallback = False

    # ---- Public API ----

    def put(self, execution_id: str, node_id: str, file_path: str,
            content: str, metadata: dict | None = None, ttl: int | None = None) -> str:
        """存储工件，返回引用 key。"""
        version = self._next_version(execution_id, file_path)
        key = self._make_key(execution_id, node_id, file_path, version)

        artifact = Artifact(
            key=key,
            file_path=file_path,
            content=content,
            line_count=content.count("\n") + 1,
            metadata=metadata or {},
            created_by=node_id,
            created_at=time.time(),
            ttl=ttl or self.default_ttl,
        )

        data = {
            "file_path": artifact.file_path,
            "content": artifact.content,
            "line_count": artifact.line_count,
            "metadata": json.dumps(artifact.metadata),
            "created_by": artifact.created_by,
            "created_at": str(artifact.created_at),
        }

        actual_ttl = ttl or self.default_ttl

        if self._use_fallback:
            self._fallback[key] = artifact
        else:
            self.redis.hset(key, mapping=data)
            self.redis.expire(key, actual_ttl)

        # 记录到执行索引
        idx_key = f"artifact:index:{execution_id}"
        if self._use_fallback:
            pass  # fallback 模式不需要索引
        else:
            self.redis.sadd(idx_key, key)
            self.redis.expire(idx_key, actual_ttl + 60)

        return key

    def get(self, key: str) -> Optional[Artifact]:
        """按 key 获取完整工件。"""
        if self._use_fallback:
            return self._fallback.get(key)

        data = self.redis.hgetall(key)
        if not data:
            return None

        return Artifact(
            key=key,
            file_path=data.get("file_path", ""),
            content=data.get("content", ""),
            line_count=int(data.get("line_count", 0)),
            metadata=json.loads(data.get("metadata", "{}")),
            created_by=data.get("created_by", ""),
            created_at=float(data.get("created_at", "0")),
        )

    def get_range(self, key: str, start_line: int, end_line: int) -> Optional[str]:
        """获取工件的指定行范围（1-based，含两端）。"""
        artifact = self.get(key)
        if artifact is None:
            return None

        lines = artifact.content.split("\n")
        # 转换为 0-based
        start = max(0, start_line - 1)
        end = min(len(lines), end_line)
        if start >= len(lines):
            return ""
        return "\n".join(lines[start:end])

    def resolve_refs(self, text: str) -> str:
        """解析文本中的所有 [REF: artifact://...] 引用，替换为实际内容。

        引用语法:
            [REF: artifact://key]              → 完整内容
            [REF: artifact://key#L10-L50]      → 第 10-50 行
            [REF: artifact://key#L42]          → 单行
        """
        import re

        def _resolve(match):
            full_ref = match.group(0)
            inner = match.group(1)  # 去掉 [REF: 和 ]

            # 解析 key 和行号范围
            range_part = None
            if "#L" in inner:
                inner, range_part = inner.split("#L", 1)

            # 去掉 artifact:// 前缀
            key = inner.replace("artifact://", "")

            # 获取内容
            if range_part:
                if "-" in range_part:
                    parts = range_part.split("-")
                    start = int(parts[0])
                    end = int(parts[1])
                    content = self.get_range(key, start, end)
                else:
                    line = int(range_part)
                    content = self.get_range(key, line, line)
                if content:
                    return f"// [artifact://{key}#L{range_part}]\n{content}\n// [/REF]"
                else:
                    return f"[REF NOT FOUND: {key}#L{range_part}]"
            else:
                artifact = self.get(key)
                if artifact:
                    return f"// [artifact://{key}]\n{artifact.content}\n// [/REF]"
                else:
                    return f"[REF NOT FOUND: {key}]"

        return re.sub(r'\[REF:\s*artifact://[^\]]+\]', _resolve, text)

    def list_keys(self, execution_id: str) -> list[str]:
        """列出一次执行的所有工件 key。"""
        if self._use_fallback:
            return [k for k in self._fallback if execution_id in k]

        idx_key = f"artifact:index:{execution_id}"
        return list(self.redis.smembers(idx_key))

    def cleanup(self, execution_id: str) -> int:
        """清理一次执行的所有工件，返回清理数量。"""
        keys = self.list_keys(execution_id)
        if not keys:
            return 0

        if self._use_fallback:
            count = 0
            for k in list(keys):
                if k in self._fallback:
                    del self._fallback[k]
                    count += 1
            return count

        count = self.redis.delete(*keys) if keys else 0
        self.redis.delete(f"artifact:index:{execution_id}")
        return count

    # ---- Private ----

    def _make_key(self, execution_id: str, node_id: str, file_path: str,
                  version: int) -> str:
        fname = file_path.replace("\\", "/").split("/")[-1]
        return f"artifact:{execution_id}:{node_id}:{fname}:v{version}"

    def _next_version(self, execution_id: str, file_path: str) -> int:
        """为同一文件生成递增版本号。"""
        fname = file_path.replace("\\", "/").split("/")[-1]
        pattern = f"artifact:{execution_id}:*:{fname}:v*"
        if self._use_fallback:
            existing = [k for k in self._fallback if k.startswith(f"artifact:{execution_id}:") and fname in k]
            return len(existing) + 1

        existing = self.redis.keys(pattern)
        return len(existing) + 1


# 模块级单例
_store: Optional[ArtifactStore] = None


def get_artifact_store(host: str = "localhost", port: int = 6379) -> ArtifactStore:
    global _store
    if _store is None:
        _store = ArtifactStore(host=host, port=port)
    return _store
