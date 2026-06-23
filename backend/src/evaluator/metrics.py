"""
FlowForge v0.2 - 评估指标计算（扩展版）
增加 Agent 特有指标：工具调用次数、工具成功率、Agent 周转数。
"""
from typing import Any


def compute_metrics(details: list[dict]) -> dict:
    """从详情列表计算汇总指标（v0.2 扩展版）。"""
    total = len(details)
    if total == 0:
        return _empty_metrics()

    successful = [d for d in details if d.get("success")]
    latencies = [d.get("latency_ms", 0) for d in details]
    tokens = [d.get("tokens", 0) for d in details]
    tool_calls = [d.get("tool_calls", 0) for d in details]
    tool_errors = [d.get("tool_errors", 0) for d in details]

    total_tool_calls = sum(tool_calls)
    total_tool_errors = sum(tool_errors)

    return {
        # v0.1 基本指标
        "success_rate": round(len(successful) / total, 4),
        "avg_latency_ms": sum(latencies) // total,
        "avg_tokens": sum(tokens) // total,
        "total_cost_estimate": round(sum(tokens) * 0.000001, 4),
        "total_questions": total,
        "passed": len(successful),
        "failed": total - len(successful),
        # v0.2 Agent 指标
        "total_tool_calls": total_tool_calls,
        "total_tool_errors": total_tool_errors,
        "tool_success_rate": (
            round((total_tool_calls - total_tool_errors) / max(total_tool_calls, 1), 4)
        ),
        "avg_tool_calls_per_question": round(total_tool_calls / total, 1),
        "max_latency_ms": max(latencies) if latencies else 0,
        "min_latency_ms": min(latencies) if latencies else 0,
    }


def _empty_metrics() -> dict:
    return {
        "success_rate": 0, "avg_latency_ms": 0, "avg_tokens": 0,
        "total_cost_estimate": 0, "total_questions": 0, "passed": 0, "failed": 0,
        "total_tool_calls": 0, "total_tool_errors": 0,
        "tool_success_rate": 0, "avg_tool_calls_per_question": 0,
        "max_latency_ms": 0, "min_latency_ms": 0,
    }


def compute_category_breakdown(details: list[dict]) -> dict[str, dict]:
    """按 category 分组计算指标。"""
    cats: dict[str, list[dict]] = {}
    for d in details:
        cat = d.get("category", "uncategorized")
        cats.setdefault(cat, []).append(d)
    return {cat: compute_metrics(items) for cat, items in cats.items()}
