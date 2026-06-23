"""
FlowForge v0.2 - 架构对比（扩展版）
加载多个评估结果，计算差距，包含 Agent 工具指标对比。
"""
from typing import Any


def compare_evaluations(runs: list[dict]) -> dict:
    """对比多个评估运行的结果。

    Args:
        runs: 列表，每个元素是 {architecture_name, summary, details}

    Returns:
        包含对比表和差异分析的字典
    """
    if len(runs) < 2:
        return {"runs": runs, "diff": {}, "message": "Need at least 2 runs to compare"}

    comparison_table = []
    for i, run in enumerate(runs):
        summary = run.get("summary", {})
        comparison_table.append({
            "name": run.get("name", f"Run {i + 1}"),
            "success_rate": summary.get("success_rate", 0),
            "avg_latency_ms": summary.get("avg_latency_ms", 0),
            "avg_tokens": summary.get("avg_tokens", 0),
            "total_cost": summary.get("total_cost_estimate", 0),
            "passed": summary.get("passed", 0),
            "failed": summary.get("failed", 0),
            "total_tool_calls": summary.get("total_tool_calls", 0),
            "tool_success_rate": summary.get("tool_success_rate", 0),
            "avg_tool_calls_per_question": summary.get("avg_tool_calls_per_question", 0),
        })

    # 计算差异（以第一个为基准）
    base = comparison_table[0]
    diffs = []
    for i, row in enumerate(comparison_table[1:], 1):
        diffs.append({
            "comparison": f"{base['name']} vs {row['name']}",
            "success_rate_delta": round(row["success_rate"] - base["success_rate"], 4),
            "latency_delta_ms": row["avg_latency_ms"] - base["avg_latency_ms"],
            "tokens_delta": row["avg_tokens"] - base["avg_tokens"],
            "cost_delta": round(row["total_cost"] - base["total_cost"], 4),
            "tool_calls_delta": row["total_tool_calls"] - base["total_tool_calls"],
            "tool_success_rate_delta": round(row["tool_success_rate"] - base["tool_success_rate"], 4),
            "winner": _determine_winner(base, row, f"Run {i + 1}"),
        })

    return {
        "runs": runs,
        "comparison_table": comparison_table,
        "diffs": diffs,
    }


def _determine_winner(base: dict, challenger: dict, challenger_name: str) -> str:
    """综合评判：成功率(40%) + 延迟(20%) + 成本(20%) + 工具效率(20%)。"""
    base_score = 0
    chal_score = 0

    # 成功率（权重 40%）
    if challenger["success_rate"] > base["success_rate"]:
        chal_score += 40
    elif challenger["success_rate"] < base["success_rate"]:
        base_score += 40

    # 延迟（权重 20%）- 越低越好
    if challenger["avg_latency_ms"] < base["avg_latency_ms"]:
        chal_score += 20
    elif challenger["avg_latency_ms"] > base["avg_latency_ms"]:
        base_score += 20

    # 成本（权重 20%）- 越低越好
    if challenger["total_cost"] < base["total_cost"]:
        chal_score += 20
    elif challenger["total_cost"] > base["total_cost"]:
        base_score += 20

    # 工具效率（权重 20%）- 工具调用少 + 成功率高 = 更优
    chal_tool_eff = (challenger.get("tool_success_rate", 0) * 10) - challenger.get("avg_tool_calls_per_question", 0)
    base_tool_eff = (base.get("tool_success_rate", 0) * 10) - base.get("avg_tool_calls_per_question", 0)
    if chal_tool_eff > base_tool_eff:
        chal_score += 20
    elif chal_tool_eff < base_tool_eff:
        base_score += 20

    if chal_score > base_score:
        return challenger_name
    elif base_score > chal_score:
        return base["name"]
    else:
        return "tie"
