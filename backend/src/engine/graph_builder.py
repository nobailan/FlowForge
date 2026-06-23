"""
FlowForge v0.1 - 动态 LangGraph 构建器
将画布 JSON（nodes + edges）编译为可执行的 LangGraph StateGraph。

核心逻辑：
1. 遍历 nodes → 查 registry → factory(node_id, config) → node_fn
2. 拓扑分析 → 找入口节点（in_degree=0）
3. 遍历 edges → add_edge / add_conditional_edges
4. 终端节点 → END
"""
import time
from langgraph.graph import StateGraph, END

from .state import AgentState
from .registry import get_registry
from .monitor import EventBus, NodeEvent


class GraphBuildError(Exception):
    """画布 JSON 无法编译为有效图时抛出。"""
    pass


class GraphBuilder:
    """从画布 JSON 构建 LangGraph StateGraph。

    如果传入 event_bus，则自动为每个节点注入监控包装器。
    """

    def __init__(self, canvas_data: dict, event_bus: EventBus | None = None):
        self.canvas = canvas_data
        self.nodes: list[dict] = canvas_data.get("nodes", [])
        self.edges: list[dict] = canvas_data.get("edges", [])
        self.registry = get_registry()
        self.event_bus = event_bus

        # 内部状态
        self._node_fn_map: dict[str, callable] = {}      # node_id -> fn (可能被监控包装)
        self._node_types: dict[str, str] = {}             # node_id -> type
        self._condition_nodes: set[str] = set()
        self._loop_nodes: set[str] = set()

    def build(self) -> StateGraph:
        """构建 StateGraph，返回未编译的图。"""
        if not self.nodes:
            raise GraphBuildError("Canvas has no nodes.")

        # 1. 验证所有节点类型在注册表中
        for node in self.nodes:
            node_id = node["id"]
            node_type = node["type"]
            if node_type not in self.registry._types:
                raise GraphBuildError(
                    f"Unknown node type '{node_type}' at node '{node_id}'. "
                    f"Available: {list(self.registry._types.keys())}"
                )

        # 2. 构建邻接表
        in_degree: dict[str, int] = {n["id"]: 0 for n in self.nodes}
        adjacency: dict[str, list[str]] = {n["id"]: [] for n in self.nodes}

        for edge in self.edges:
            src = edge["source"]
            tgt = edge.get("target", "")
            if src in adjacency:
                adjacency[src].append(tgt)
            if tgt:
                in_degree[tgt] = in_degree.get(tgt, 0) + 1

        # 3. 实例化节点函数并注入监控
        workflow = StateGraph(AgentState)

        for node in self.nodes:
            node_id = node["id"]
            node_type = node["type"]
            config = node.get("config", {})

            type_def = self.registry.get(node_type)
            merged_config = {**type_def.default_config, **config}

            factory = type_def.node_factory
            try:
                raw_fn = factory(node_id, merged_config)
            except Exception as e:
                raise GraphBuildError(f"Failed to create node '{node_id}' ({node_type}): {e}")

            self._node_types[node_id] = node_type

            if node_type == "condition":
                self._condition_nodes.add(node_id)
            if node_type == "loop":
                self._loop_nodes.add(node_id)

            # condition/loop 的 raw_fn 返回路由字符串，不能直接用作 node 函数
            # node 函数需要返回 state dict，路由函数用于 add_conditional_edges
            if node_type in ("condition", "loop"):
                # 路由函数（原样保留，给 add_conditional_edges 用）
                route_fn = raw_fn
                # node 函数：调用路由函数，返回值存 state，返回 state dict
                def _make_route_node(rid, rf):
                    def node_wrapper(s: dict) -> dict:
                        decision = rf(s)  # 路由函数内部已把结果写入 state["node_outputs"]
                        s["route_decision"] = decision
                        return s
                    return node_wrapper
                node_fn = _make_route_node(node_id, route_fn)
            else:
                route_fn = None
                node_fn = raw_fn

            # 监控包装器：跳过路由节点 + Agent 节点（后者自行处理日志）
            _skip_monitor = ("condition", "loop", "llm", "tool", "retriever", "subagent")
            if self.event_bus and node_type not in _skip_monitor:
                node_fn = self._make_monitored(node_id, node_type, node_fn)

            self._node_fn_map[node_id] = route_fn if route_fn else node_fn
            workflow.add_node(node_id, node_fn)

        # 4. 找入口节点（in_degree == 0）
        entry_candidates = [nid for nid, deg in in_degree.items() if deg == 0]
        if not entry_candidates:
            # 循环图：每个节点都有入边，取第一个节点作为入口
            workflow.set_entry_point(self.nodes[0]["id"])
        else:
            workflow.set_entry_point(entry_candidates[0])

        # 5. 构建条件/循环节点的路由表
        condition_route_maps: dict[str, dict[str, str]] = {}
        for edge in self.edges:
            src = edge["source"]
            tgt = edge.get("target", "")
            label = edge.get("label", "")
            if src in self._condition_nodes or src in self._loop_nodes:
                if src not in condition_route_maps:
                    condition_route_maps[src] = {}
                if label:
                    condition_route_maps[src][label] = tgt if tgt else END

        # 6. 添加边
        for edge in self.edges:
            src = edge["source"]
            tgt = edge.get("target", "")

            if not tgt:
                continue

            if src in self._condition_nodes or src in self._loop_nodes:
                # 条件/循环节点 → 第一次遇到时用 add_conditional_edges
                route_fn = self._node_fn_map[src]
                # 构建 route_map，未显式映射的分支默认走 END
                if src in self._loop_nodes:
                    default_map = {"continue": END, "exit": END}
                else:
                    default_map = {"true": END, "false": END}
                route_map = {**default_map, **condition_route_maps.get(src, {})}

                # 用标记避免重复添加
                route_map_key = f"_edges_added_{src}"
                if not getattr(workflow, route_map_key, False):
                    workflow.add_conditional_edges(src, route_fn, route_map)
                    setattr(workflow, route_map_key, True)
            else:
                workflow.add_edge(src, tgt)

        # 7. 终端节点 → END
        for nid, targets in adjacency.items():
            if not targets and nid not in self._condition_nodes and nid not in self._loop_nodes:
                # 检查是否已有出边
                workflow.add_edge(nid, END)

        return workflow

    def compile(self):
        """构建并编译图。"""
        graph = self.build()
        return graph.compile()

    def get_node_types(self) -> dict[str, str]:
        """获取 node_id → type 映射。"""
        return dict(self._node_types)

    # ---- private ----

    def _make_monitored(self, node_id: str, node_type: str, original_fn):
        """为节点函数注入监控包装器。"""
        event_bus = self.event_bus

        def wrapped(state: dict) -> dict:
            start = time.time()

            # emit "running"
            event_bus.emit_sync(NodeEvent(
                execution_id=event_bus.execution_id,
                node_id=node_id,
                node_type=node_type,
                status="running",
                input_summary=str(state.get("input", ""))[:200],
                output_summary="",
                latency_ms=0,
                token_count=0,
            ))

            try:
                result = original_fn(state)

                elapsed = int((time.time() - start) * 1000)

                # 路由函数返回 str
                if isinstance(result, str):
                    event_bus.emit_sync(NodeEvent(
                        execution_id=event_bus.execution_id,
                        node_id=node_id,
                        node_type=node_type,
                        status="completed",
                        input_summary="routes",
                        output_summary=result,
                        latency_ms=elapsed,
                        token_count=0,
                    ))
                    return state

                # 普通节点 - 从 node_outputs 读取最新数据
                ndata = {}
                if isinstance(result, dict):
                    ndata = result.get("node_outputs", {}).get(node_id, {})
                status = ndata.get("status", "completed")
                event_bus.emit_sync(NodeEvent(
                    execution_id=event_bus.execution_id,
                    node_id=node_id,
                    node_type=node_type,
                    status=status,
                    input_summary=str(state.get("input", ""))[:200],
                    output_summary=str(ndata.get("output", ""))[:200],
                    latency_ms=elapsed,
                    token_count=ndata.get("tokens", 0),
                ))
                return result

            except Exception as e:
                elapsed = int((time.time() - start) * 1000)
                event_bus.emit_sync(NodeEvent(
                    execution_id=event_bus.execution_id,
                    node_id=node_id,
                    node_type=node_type,
                    status="error",
                    input_summary="",
                    output_summary=str(e)[:500],
                    latency_ms=elapsed,
                    token_count=0,
                ))
                state["error"] = str(e)
                return state

        return wrapped
