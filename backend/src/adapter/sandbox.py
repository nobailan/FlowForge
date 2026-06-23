"""
工作空间管理
为每次执行创建隔离的临时工作目录。
"""
import os
import shutil
import tempfile
from pathlib import Path

WORKSPACE_ROOT = Path(tempfile.gettempdir()) / "flowforge-runs"


class WorkspaceManager:
    """管理工作空间（临时目录）的创建与清理。

    用法:
        wm = WorkspaceManager()
        path = wm.create("exec_123", "supervisor")
        # OpenCode 在 path 中执行
        wm.cleanup("exec_123")
    """

    def __init__(self, root: Path | None = None):
        self.root = root or WORKSPACE_ROOT
        self.root.mkdir(parents=True, exist_ok=True)

    def create(self, execution_id: str, node_id: str) -> str:
        """为指定节点创建工作目录。"""
        path = self.root / execution_id / node_id
        path.mkdir(parents=True, exist_ok=True)
        return str(path.absolute())

    def create_execution_root(self, execution_id: str) -> str:
        """为一次执行创建共享根目录。"""
        path = self.root / execution_id
        path.mkdir(parents=True, exist_ok=True)
        return str(path.absolute())

    def node_path(self, execution_id: str, node_id: str) -> str:
        return str((self.root / execution_id / node_id).absolute())

    def execution_path(self, execution_id: str) -> str:
        return str((self.root / execution_id).absolute())

    def cleanup(self, execution_id: str) -> None:
        """清理一次执行的所有工作目录。"""
        path = self.root / execution_id
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)

    def cleanup_all(self) -> None:
        """清理所有工作目录。"""
        if self.root.exists():
            shutil.rmtree(self.root, ignore_errors=True)
            self.root.mkdir(parents=True, exist_ok=True)

    def list_workspaces(self) -> list[str]:
        """列出所有活跃的执行 ID。"""
        if self.root.exists():
            return [d.name for d in self.root.iterdir() if d.is_dir()]
        return []
