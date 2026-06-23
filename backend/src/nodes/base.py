"""
FlowForge v0.1 - 节点基础工具
提供 @register_node 装饰器，供各节点类型注册使用。
"""
from ..engine.registry import NodeTypeDefinition, get_registry


def register_node(
    name: str,
    display_name: str,
    description: str,
    category: str,
    config_schema: dict,
    default_config: dict | None = None,
    input_ports: list[str] | None = None,
    output_ports: list[str] | None = None,
    icon: str = "default",
):
    """装饰器：注册一个节点类型工厂函数。

    用法：
        @register_node(
            name="llm",
            display_name="LLM",
            description="调用大语言模型",
            category="llm",
            config_schema={...},
            default_config={...},
        )
        def llm_node_factory(node_id: str, config: dict):
            def node_fn(state):
                ...
                return state
            return node_fn
    """
    def decorator(factory_fn):
        definition = NodeTypeDefinition(
            name=name,
            display_name=display_name,
            description=description,
            category=category,
            config_schema=config_schema,
            default_config=default_config or {},
            node_factory=factory_fn,
            input_ports=input_ports or ["input"],
            output_ports=output_ports or ["output"],
            icon=icon,
        )
        get_registry().register(definition)
        return factory_fn
    return decorator
