"""
FlowForge v0.4 - 协作模式拓扑分析引擎
分析画布 JSON → 识别协作模式 + 节点角色分类 + 合法性检查。
"""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TopologyReport:
    pattern: str = "mixed"        # fan_out_fan_in | sequential | conditional | cyclic | mixed
    entry_nodes: list[str] = field(default_factory=list)
    terminal_nodes: list[str] = field(default_factory=list)
    node_roles: dict[str, str] = field(default_factory=dict)
    is_valid: bool = True
    warnings: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


class TopologyAnalyzer:
    """分析画布拓扑结构。"""

    def analyze(self, canvas_data: dict) -> TopologyReport:
        nodes = canvas_data.get("nodes", [])
        edges = canvas_data.get("edges", [])
        report = TopologyReport()

        if not nodes:
            report.is_valid = False
            report.warnings.append("Canvas has no nodes.")
            return report

        # 1. 构建邻接表
        node_ids = {n["id"] for n in nodes}
        in_degree: dict[str, int] = {n["id"]: 0 for n in nodes}
        out_degree: dict[str, int] = {n["id"]: 0 for n in nodes}
        adjacency: dict[str, list[str]] = {n["id"]: [] for n in nodes}

        for e in edges:
            src, tgt = e["source"], e.get("target", "")
            if src not in node_ids:
                report.warnings.append(f"Edge source '{src}' not in nodes.")
                continue
            if tgt and tgt not in node_ids:
                report.warnings.append(f"Edge target '{tgt}' not in nodes.")
                continue
            adjacency[src].append(tgt)
            out_degree[src] += 1
            if tgt:
                in_degree[tgt] += 1

        # 2. 找入口/出口
        report.entry_nodes = [nid for nid, deg in in_degree.items() if deg == 0]
        report.terminal_nodes = [nid for nid, deg in out_degree.items() if deg == 0 and self._is_regular_node(nid, nodes)]

        if not report.entry_nodes:
            report.is_valid = False
            report.warnings.append("No entry node found (every node has incoming edges).")

        # 3. 检测孤点
        for nid in node_ids:
            if in_degree[nid] == 0 and out_degree[nid] == 0:
                report.warnings.append(f"Isolated node: {nid}")

        # 4. 检测循环
        has_cycle = self._detect_cycle(node_ids, adjacency)
        if has_cycle:
            report.suggestions.append("Cyclic graph detected. Ensure proper loop termination.")

        # 5. 节点角色分类
        node_types = {n["id"]: n["type"] for n in nodes}
        for nid in node_ids:
            role = self._classify_role(nid, in_degree, out_degree, node_types, adjacency, edges)
            report.node_roles[nid] = role

        # 6. 模式识别
        report.pattern = self._identify_pattern(report, node_types, in_degree, out_degree, adjacency)

        # 7. 合法性检查
        self._validate(nodes, edges, node_types, adjacency, report)

        # 8. 生成建议
        self._generate_suggestions(report)

        return report

    def _is_regular_node(self, nid: str, nodes: list[dict]) -> bool:
        """非 condition/loop 的普通节点。"""
        for n in nodes:
            if n["id"] == nid:
                return n["type"] not in ("condition", "loop")
        return True

    def _classify_role(self, nid: str, in_d: dict, out_d: dict,
                       node_types: dict, adj: dict, edges: list) -> str:
        nt = node_types.get(nid, "llm")
        indeg = in_d.get(nid, 0)
        outdeg = out_d.get(nid, 0)

        if nt == "condition":
            return "router"
        if nt == "loop":
            return "loop_controller"

        if indeg == 0 and outdeg > 1:
            return "dispatcher"
        if indeg > 1 and outdeg == 0:
            return "aggregator"
        if indeg >= 1 and outdeg >= 1:
            # 检查是否在 fan-in + fan-out 交汇点
            if indeg > 1 and outdeg > 0:
                return "coordinator"
            return "worker"
        if indeg == 0 and outdeg == 1:
            return "entry_worker"
        if indeg > 0 and outdeg == 0:
            return "leaf_worker"

        return "unknown"

    def _identify_pattern(self, report: TopologyReport, node_types: dict,
                          in_d: dict, out_d: dict, adj: dict) -> str:
        roles = report.node_roles
        has_router = any(r == "router" for r in roles.values())
        has_loop = any(r == "loop_controller" for r in roles.values())
        has_dispatcher = any(r == "dispatcher" for r in roles.values())
        has_aggregator = any(r == "aggregator" for r in roles.values())
        has_coordinator = any(r == "coordinator" for r in roles.values())
        worker_count = sum(1 for r in roles.values() if r in ("worker", "entry_worker", "leaf_worker"))

        # 检测循环
        if self._detect_cycle(set(roles.keys()), adj):
            return "cyclic"

        # Fan-out fan-in: dispatcher + workers + aggregator
        if has_dispatcher and has_aggregator:
            return "fan_out_fan_in"
        if has_dispatcher and not has_aggregator:
            return "fan_out"

        # Coordinator (类似 supervisor-worker 但没有明确 dispatcher)
        if has_coordinator and worker_count >= 2:
            return "fan_out_fan_in"

        # Conditional
        if has_router:
            return "conditional"

        # Sequential: all nodes have indegree <= 1 and outdegree <= 1
        all_simple = all(in_d.get(nid, 0) <= 1 and out_d.get(nid, 0) <= 1
                         for nid in roles)
        if all_simple and not has_router and not has_loop:
            return "sequential"

        return "mixed"

    def _detect_cycle(self, node_ids: set, adj: dict) -> bool:
        """Kahn 算法检测是否有环。"""
        in_degree = {nid: 0 for nid in node_ids}
        for nid, targets in adj.items():
            for t in targets:
                if t in in_degree:
                    in_degree[t] += 1

        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        visited = 0

        while queue:
            nid = queue.pop(0)
            visited += 1
            for t in adj.get(nid, []):
                if t in in_degree:
                    in_degree[t] -= 1
                    if in_degree[t] == 0:
                        queue.append(t)

        return visited < len(node_ids)

    def _validate(self, nodes: list, edges: list, node_types: dict,
                  adj: dict, report: TopologyReport):
        for n in nodes:
            nid = n["id"]
            nt = n["type"]
            out_edges = [e for e in edges if e["source"] == nid]

            if nt == "condition" and out_edges:
                labels = {e.get("label", "") for e in out_edges}
                if not labels or labels == {""}:
                    report.warnings.append(
                        f"Condition node '{nid}' has unlabeled outgoing edges. Add true/false labels.")

            if nt == "loop" and out_edges:
                labels = {e.get("label", "") for e in out_edges}
                if not labels or labels == {""}:
                    report.warnings.append(
                        f"Loop node '{nid}' has unlabeled outgoing edges. Add continue/exit labels.")

    def _generate_suggestions(self, report: TopologyReport):
        p = report.pattern
        if p == "fan_out_fan_in":
            report.suggestions.append(
                "Fan-out/Fan-in pattern: dispatcher should decompose tasks. Workers should only do assigned work. Aggregator should merge results.")
        elif p == "sequential":
            report.suggestions.append(
                "Sequential pattern: each step should only pass necessary data to the next step. Use {{prev.output}} templates.")
        elif p == "conditional":
            report.suggestions.append(
                "Conditional pattern: ensure classifier outputs a clear label. Condition field should match the classifier's output format.")
        elif p == "cyclic":
            report.suggestions.append(
                "Cyclic/Loop pattern: ensure the reflector clearly outputs SATISFIED or NEEDS_IMPROVEMENT. Set reasonable max_iterations.")
        elif p == "mixed":
            report.suggestions.append(
                "Mixed topology: consider simplifying to a standard pattern for better predictability.")


def analyze_topology(canvas_data: dict) -> TopologyReport:
    """便捷函数。"""
    return TopologyAnalyzer().analyze(canvas_data)
