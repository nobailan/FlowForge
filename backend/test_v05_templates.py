"""
FlowForge v0.5 — 5 模板全量测试 + Token 对比估算
"""
import time
import json
import asyncio

# 注册节点类型
import src.nodes  # noqa
from src.engine.graph_builder import GraphBuilder
from src.engine.state import create_initial_state
from src.engine.templates import TEMPLATES

# 简单测试用的任务描述（Token 消耗小）
TEST_INPUTS = {
    "supervisor_worker": "What is 2+2? Answer ONLY a number.",
    "sequential_chain": "Step 1: say HELLO. Step 2: say WORLD.",
    "parallel": "Is the sky blue? Answer yes or no.",
    "conditional_branch": "Is 5 greater than 3?",
    "reflection_loop": "Spell the word: CAT",
}

# v0.4 Token 估算参数（基于经验值）
V04_TOOLS_PER_NODE = 800     # 每个节点全工具定义的 Token 数
V04_OUTPUT_BLOAT = 500       # 每个节点啰嗦输出的额外 Token
V04_NO_JSON = 200            # 无 JSON 约束导致的多余文本
V05_TOOL_TOKEN = 150         # 每个工具的 Token 数
V05_JSON_SAVING = 300        # JSON 约束节省的输出 Token
V05_REF_SAVING_PER_FILE = 5000  # 工件存储每次节省的文件传递 Token


def count_tools(config: dict) -> int:
    return len(config.get("allowed_tools", []) or [])


async def run_template(name: str, template: dict, input_text: str) -> dict:
    """运行一个模板，返回结果。"""
    canvas = template["canvas_data"]
    nodes = canvas["nodes"]
    edges = canvas["edges"]

    print(f"\n{'='*60}")
    print(f"  {name} — {len(nodes)} nodes, {len(edges)} edges")
    print(f"{'='*60}")

    start = time.time()

    builder = GraphBuilder(canvas)
    graph = builder.build()
    agent = graph.compile()
    state = create_initial_state(input_text)

    error = None
    try:
        result = await asyncio.to_thread(
            agent.invoke, state,
            {"configurable": {"thread_id": f"test_{name}"}}
        )
    except Exception as e:
        error = str(e)
        result = {}

    elapsed = time.time() - start

    node_outputs = result.get("node_outputs", {}) if result else {}
    total_tokens = result.get("total_tokens", 0) if result else 0

    # 逐节点分析
    node_results = []
    for node in nodes:
        nid = node["id"]
        ntype = node["type"]
        ndata = node_outputs.get(nid, {})
        status = ndata.get("status", "error" if error else "skipped")
        tokens = ndata.get("tokens", 0)
        latency = ndata.get("latency_ms", 0)
        output = str(ndata.get("output", ""))[:100]
        cfg = node.get("config", {})
        tool_count = count_tools(cfg)
        node_results.append({
            "id": nid, "type": ntype, "status": status,
            "tokens": tokens, "latency_ms": latency,
            "tools": tool_count, "output_preview": output,
        })

        icon = "✅" if status == "completed" else "❌"
        print(f"  {icon} {nid} ({ntype}) {status} | {tokens}T {latency}ms "
              f"| tools={tool_count} | {output[:60]}")

    status = "completed" if not error else "failed"
    print(f"  {'─'*50}")
    print(f"  Total: {total_tokens}T | {elapsed:.1f}s | {status}")

    return {
        "template": name,
        "status": status,
        "total_tokens": total_tokens,
        "elapsed_sec": elapsed,
        "nodes": node_results,
        "error": error,
    }


def estimate_v04_tokens(template_name: str, nodes: list) -> int:
    """估算 v0.4 同等流程的 Token 消耗。"""
    agent_nodes = [n for n in nodes if n["type"] != "condition"]
    num_agents = len(agent_nodes)

    # v0.4: 每个节点全工具 + 啰嗦输出 + 无 JSON 约束
    base_tokens = 1500  # 任务 + 基础上下文
    tools_overhead = V04_TOOLS_PER_NODE * num_agents
    output_bloat = V04_OUTPUT_BLOAT * num_agents
    no_json = V04_NO_JSON * num_agents

    # 多节点流程：文件值传递（假设 2 个 worker 传递文件）
    file_passing = 0
    if template_name in ("supervisor_worker", "parallel"):
        file_passing = V04_REF_SAVING_PER_FILE * 2  # Worker 间传递 2 次

    return base_tokens + tools_overhead + output_bloat + no_json + file_passing


def estimate_v05_saving(actual_tokens: int, v04_estimate: int) -> float:
    """计算节省百分比。"""
    if v04_estimate == 0:
        return 0
    return (1 - actual_tokens / v04_estimate) * 100


async def main():
    print("=" * 60)
    print("  FlowForge v0.5 — 5 Template Test Suite")
    print("=" * 60)
    print(f"  Redis: checking... ", end="")
    try:
        from src.engine.artifact_store import get_artifact_store
        store = get_artifact_store()
        store.redis.ping()
        print("OK")
    except Exception as e:
        print(f"WARNING: {e}")

    results = []
    for name in ["supervisor_worker", "sequential_chain", "parallel",
                  "conditional_branch", "reflection_loop"]:
        template = TEMPLATES.get(name)
        if not template:
            print(f"  SKIP {name}: template not found")
            continue
        result = await run_template(name, template, TEST_INPUTS[name])
        results.append(result)

    # ========================================
    # 汇总报告
    # ========================================
    print(f"\n\n{'='*60}")
    print(f"  TOKEN SAVING REPORT (v0.4 → v0.5)")
    print(f"{'='*60}")

    total_actual = 0
    total_estimated_v04 = 0
    all_passed = True

    for r in results:
        name = r["template"]
        actual = r["total_tokens"]
        nodes = r["nodes"]
        v04_est = estimate_v04_tokens(name, TEMPLATES[name]["canvas_data"]["nodes"])
        saving = estimate_v05_saving(actual, v04_est)
        total_actual += actual
        total_estimated_v04 += v04_est

        status = "PASS" if r["status"] == "completed" else "FAIL"
        if r["status"] != "completed":
            all_passed = False

        tool_summary = ", ".join(
            f"{nd['id']}({nd['tools']}t)" for nd in nodes if nd["type"] != "condition"
        )

        print(f"\n  [{status}] {name}")
        print(f"    v0.4 est: {v04_est:,}T → v0.5 actual: {actual:,}T")
        print(f"    Saving: {saving:.0f}% | {r['elapsed_sec']:.0f}s")
        print(f"    Tools per node: {tool_summary}")
        if r["error"]:
            print(f"    Error: {r['error'][:200]}")

    overall_saving = estimate_v05_saving(total_actual, total_estimated_v04)

    print(f"\n  {'='*50}")
    print(f"  OVERALL")
    print(f"  v0.4 estimated: {total_estimated_v04:,}T")
    print(f"  v0.5 actual:    {total_actual:,}T")
    print(f"  Saving:         {overall_saving:.0f}%")
    print(f"  All passed:     {all_passed}")

    # 按优化项分解
    print(f"\n  SAVING BREAKDOWN (per typical 4-node flow)")
    print(f"  {'Optimization':<30} {'v0.4':>8} {'v0.5':>8} {'Saved':>8}")
    print(f"  {'-'*54}")
    items = [
        ("Tool definitions", V04_TOOLS_PER_NODE * 4, V05_TOOL_TOKEN * 6, ""),
        ("Output bloat (JSON)", V04_OUTPUT_BLOAT * 4, 100 * 4, ""),
        ("No JSON constraint", V04_NO_JSON * 4, 0, ""),
        ("File value passing", V04_REF_SAVING_PER_FILE, 50, "(with ArtifactStore)"),
        ("System prompt overhead", 600, 400, "(English concise)"),
    ]
    for label, v04, v05, note in items:
        saved = v04 - v05
        print(f"  {label:<30} {v04:>6}T {v05:>6}T {saved:>6}T {note}")

    print(f"\n  Done. {'All templates working!' if all_passed else 'Some failures - see above.'}")

    # 清理 Redis
    try:
        store = get_artifact_store()
        store.cleanup("test_supervisor_worker")
        store.cleanup("test_sequential_chain")
        store.cleanup("test_parallel")
        store.cleanup("test_conditional_branch")
        store.cleanup("test_reflection_loop")
    except Exception:
        pass


if __name__ == "__main__":
    asyncio.run(main())
