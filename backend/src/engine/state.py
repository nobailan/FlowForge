"""
FlowForge v0.1 - Agent 状态定义
所有可变字段使用 Annotated + reducer，支持并行 fan-out。
"""
from typing import TypedDict, Annotated, Any
from operator import add
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


def _keep_last(a, b):
    """Reducer: 保留后一个值（用于并行分支不冲突的字段）。"""
    return b


def _merge_dicts(a: dict, b: dict) -> dict:
    """Reducer: 合并两个 dict，b 的键覆盖 a。"""
    return {**a, **b}


def _merge_lists(a: list, b: list) -> list:
    """Reducer: 拼接两个 list。"""
    return a + b


class AgentState(TypedDict, total=False):
    """FlowForge 统一的 Agent 状态。

    所有字段使用 Annotated + reducer，确保并行 fan-out 时不会
    出现 INVALID_CONCURRENT_GRAPH_UPDATE 错误。
    """

    # ---- 核心字段 ----
    messages: Annotated[list[Any], add_messages]
    input: Annotated[str, _keep_last]

    # ---- 动态节点输出 ----
    node_outputs: Annotated[dict[str, Any], _merge_dicts]

    # ---- 控制流 ----
    current_node: Annotated[str, _keep_last]
    route_decision: Annotated[str, _keep_last]
    error: Annotated[str, _keep_last]

    # ---- 最终输出 ----
    final_output: Annotated[str, _keep_last]
    total_tokens: Annotated[int, add]
    total_latency_ms: Annotated[int, add]

    # ---- 监控时间线 ----
    node_timeline: Annotated[list[dict], _merge_lists]


def create_initial_state(user_input: str) -> dict:
    """创建初始状态。返回普通 dict，LangGraph 会按 Annotated 规则合并。"""
    return {
        "messages": [],
        "input": user_input,
        "node_outputs": {},
        "current_node": "",
        "route_decision": "",
        "error": "",
        "final_output": "",
        "total_tokens": 0,
        "total_latency_ms": 0,
        "node_timeline": [],
    }
