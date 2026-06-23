"""
FlowForge v0.1 - 节点类型注册中心
装饰器驱动的插件系统 —— 每种节点类型通过 @register_node 自动注册。
"""
from typing import Dict, Any, Callable, List, Optional
from dataclasses import dataclass, field


@dataclass
class NodeTypeDefinition:
    """节点类型定义 —— 描述一种可在画布上使用的节点。"""
    name: str                           # 类型标识 (e.g., "llm", "tool")
    display_name: str                   # 展示名 (e.g., "LLM 节点")
    description: str                    # 功能描述
    category: str                       # 分组 ("llm" | "tool" | "retrieval" | "control")
    config_schema: Dict[str, Any]       # JSON Schema dict —— 前端据此渲染配置表单
    default_config: Dict[str, Any]       # 默认配置值
    node_factory: Callable              # (node_id, config) -> node_fn(state) -> state
    input_ports: List[str] = field(default_factory=lambda: ["input"])
    output_ports: List[str] = field(default_factory=lambda: ["output"])
    icon: str = "default"


class NodeRegistry:
    """节点类型注册中心（单例）。

    用法：
        registry = NodeRegistry()
        definition = NodeTypeDefinition(...)
        registry.register(definition)
        # 或者用 nodes/base.py 中的 @register_node 装饰器
    """

    _instance: Optional["NodeRegistry"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._types: Dict[str, NodeTypeDefinition] = {}
        return cls._instance

    def register(self, definition: NodeTypeDefinition) -> None:
        """注册一个节点类型。"""
        self._types[definition.name] = definition

    def get(self, name: str) -> NodeTypeDefinition:
        """获取指定类型的定义。"""
        if name not in self._types:
            raise KeyError(
                f"Unknown node type: '{name}'. "
                f"Registered types: {list(self._types.keys())}"
            )
        return self._types[name]

    def list_all(self) -> List[NodeTypeDefinition]:
        """列出所有已注册类型。"""
        return list(self._types.values())

    def list_categories(self) -> Dict[str, List[NodeTypeDefinition]]:
        """按 category 分组 —— 供前端调色板使用。"""
        cats: Dict[str, List[NodeTypeDefinition]] = {}
        for t in self._types.values():
            cats.setdefault(t.category, []).append(t)
        return cats

    def get_config_schemas(self) -> Dict[str, Dict[str, Any]]:
        """返回 {type_name: config_schema} 映射 —— 供前端获取。"""
        return {name: t.config_schema for name, t in self._types.items()}

    def clear(self):
        """清空注册表（仅用于测试）。"""
        self._types.clear()


def get_registry() -> NodeRegistry:
    """获取全局注册表单例。"""
    return NodeRegistry()
