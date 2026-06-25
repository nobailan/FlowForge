"""
FlowForge v0.5 - Prompt 自动生成引擎
Token 优化版：强制 JSON 输出 + 工具按需分配 + 英文强力约束。
"""
from dataclasses import dataclass, field
from .topology import TopologyReport

# ============================================================
# 工具分配策略 —— 第三刀：按需加载
# ============================================================

# 角色 → 允许的工具列表（空列表 = 不允许任何工具）
TOOL_ASSIGNMENT: dict[str, list[str]] = {
    "dispatcher": [],           # 只分配任务，不需要工具
    "aggregator": [],           # 只汇总结果，不需要工具
    "reader_worker": ["read", "grep", "glob"],
    "writer_worker": ["read", "write", "bash"],
    "researcher": ["web_search", "web_fetch", "read"],
    "code_worker": ["read", "write", "bash", "grep"],
    "router": [],               # 条件路由，无需工具
    "loop_controller": [],      # 循环控制，无需工具
    "unknown": [],
}

# 关键词 → worker 子类型
WORKER_KEYWORDS: dict[str, list[str]] = {
    "reader_worker": ["read", "查看", "检查", "review", "analyze", "分析", "审计", "audit", "inspect", "scan", "扫描"],
    "writer_worker": ["write", "修改", "写入", "create", "创建", "生成", "generate", "refactor", "重构", "update", "更新", "add", "添加"],
    "researcher": ["search", "搜索", "查找", "research", "调研", "find", "discover", "explore"],
    "code_worker": ["implement", "实现", "开发", "debug", "build", "构建", "deploy", "部署", "test", "测试", "fix", "修复", "bug", "漏洞", "patch", "补丁", "run", "运行", "execute", "执行"],
}

# 优先级：code > writer > researcher > reader（越"危险"的越要限制工具）
ROLE_PRIORITY = ["code_worker", "writer_worker", "researcher", "reader_worker"]


def classify_worker(task_text: str) -> str:
    """根据任务描述关键词推断 worker 子类型。"""
    text_lower = task_text.lower()
    scores: dict[str, int] = {}
    for role, keywords in WORKER_KEYWORDS.items():
        scores[role] = sum(1 for kw in keywords if kw.lower() in text_lower)
    if not scores or max(scores.values()) == 0:
        return "reader_worker"  # 默认只读
    # 有多个匹配时，按优先级选择（限制更多的角色优先）
    best_score = max(scores.values())
    for role in ROLE_PRIORITY:
        if scores.get(role, 0) == best_score:
            return role
    return max(scores, key=scores.get)  # 回退


def get_tools_for_role(role: str, task_text: str = "") -> list[str]:
    """获取指定角色应挂载的工具列表。"""
    if role in ("dispatcher", "aggregator", "router", "loop_controller"):
        return TOOL_ASSIGNMENT.get(role, [])
    if role in ("worker", "entry_worker", "leaf_worker", "coordinator"):
        sub_type = classify_worker(task_text)
        return TOOL_ASSIGNMENT.get(sub_type, [])
    return TOOL_ASSIGNMENT.get(role, [])


# ============================================================
# JSON 输出 Schema —— 第二刀：让 Worker 闭嘴
# ============================================================

# 各角色的强制 JSON 输出模板（注入到 system_prompt 末尾）
OUTPUT_SCHEMAS: dict[str, str] = {
    "dispatcher": """
OUTPUT FORMAT (MANDATORY — NO text outside JSON):
{"plan": [{"worker_id": "...", "task": "specific task description, max 200 chars", "expected_refs": []}]}
DO NOT execute any task yourself. DO NOT use tools. Output ONLY this JSON.
""",

    "worker": """
OUTPUT FORMAT (MANDATORY — NO text outside JSON):
{"status": "ok"|"error", "result": "<concise result, max 300 chars>", "refs": ["artifact://..."], "insights": []}
If you used [REF: artifact://...] in your work, list those refs.
DO NOT output explanations, reasoning, or markdown. Output ONLY this JSON.
""",

    "aggregator": """
OUTPUT FORMAT (MANDATORY — NO text outside JSON):
{"answer": "<final comprehensive answer>", "sources": [{"ref": "artifact://...", "relevance": "..."}], "confidence": 0.0-1.0}
Synthesize ALL upstream results into one cohesive answer. DO NOT re-execute any task. Output ONLY this JSON.
""",

    "entry_worker": """
OUTPUT FORMAT (MANDATORY — NO text outside JSON):
{"status": "ok"|"error", "result": "<concise result, max 300 chars>", "refs": ["artifact://..."]}
You are step 1 of a pipeline. Process ONLY your step. Output ONLY this JSON.
""",

    "leaf_worker": """
OUTPUT FORMAT (MANDATORY — NO text outside JSON):
{"status": "ok"|"error", "result": "<final answer, max 500 chars>", "refs": []}
You are the final node. Output ONLY this JSON.
""",

    "coordinator": """
OUTPUT FORMAT (MANDATORY — NO text outside JSON):
{"assignments": [{"node_id": "...", "task": "...", "tools": [...]}], "summary": "<brief coordination note, max 100 chars>"}
DO NOT execute tasks yourself. Output ONLY this JSON.
""",
}

# ============================================================
# Data Classes
# ============================================================

@dataclass
class NodePrompt:
    system_prompt: str = ""
    user_prompt_template: str = "{{input}}"
    allowed_tools: list[str] = field(default_factory=list)
    output_schema: str = ""


@dataclass
class PromptsResult:
    prompts: dict[str, NodePrompt] = field(default_factory=dict)
    topology: dict = field(default_factory=dict)


# ============================================================
# 主 Prompt 模板 —— 英文 + 强力约束
# ============================================================

# 角色 → NodePrompt（基模）
ROLE_TEMPLATES: dict[str, NodePrompt] = {}


def _build_role_templates() -> dict[str, NodePrompt]:
    """构建角色模板字典。"""
    return {
        "dispatcher": NodePrompt(
            system_prompt=(
                "You are a Task Dispatcher. Your ONLY job is to decompose the user's request "
                "into independent subtasks and assign each to a specific downstream worker.\n"
                "DO NOT execute any task yourself. DO NOT use any tools.\n"
                "Each subtask must be specific and self-contained.\n"
                "Output ONLY the required JSON structure."
            ),
            user_prompt_template="{{input}}",
        ),
        "aggregator": NodePrompt(
            system_prompt=(
                "You are a Result Aggregator. Your ONLY job is to combine outputs from "
                "upstream workers into one clear, comprehensive final answer.\n"
                "DO NOT re-execute any task. DO NOT use any tools.\n"
                "Reference artifacts by their [REF: artifact://...] identifiers.\n"
                "Output ONLY the required JSON structure."
            ),
            user_prompt_template="",
        ),
        "worker": NodePrompt(
            system_prompt=(
                "You are Worker {worker_index}. You MUST ONLY complete the specific subtask "
                "assigned to you in the [Worker{worker_index}] section.\n"
                "DO NOT do other workers' tasks. DO NOT create reports or summaries.\n"
                "Use [REF: artifact://key#Lstart-Lend] to reference file content instead of copying it.\n"
                "Output ONLY the required JSON structure — no explanations, no markdown."
            ),
            user_prompt_template="Dispatcher Plan:\n{DISPATCHER_OUTPUT}",
        ),
        "entry_worker": NodePrompt(
            system_prompt=(
                "You are the entry node of a pipeline. Process ONLY the user's input and "
                "complete ONLY step 1 of the workflow.\n"
                "DO NOT attempt to complete the entire task.\n"
                "Output ONLY the required JSON structure."
            ),
            user_prompt_template="{{input}}",
        ),
        "leaf_worker": NodePrompt(
            system_prompt=(
                "You are the final node of this pipeline. Synthesize all upstream results "
                "into the final answer.\n"
                "Be concise. DO NOT add new analysis. DO NOT use tools unless essential.\n"
                "Output ONLY the required JSON structure."
            ),
            user_prompt_template="",
        ),
        "coordinator": NodePrompt(
            system_prompt=(
                "You are a Coordinator. Receive upstream input and coordinate downstream "
                "workers to complete the task.\n"
                "DO NOT execute tasks yourself. Only assign and coordinate.\n"
                "Output ONLY the required JSON structure."
            ),
            user_prompt_template="{{input}}",
        ),
        "router": NodePrompt(system_prompt="", user_prompt_template=""),
        "loop_controller": NodePrompt(system_prompt="", user_prompt_template=""),
        "unknown": NodePrompt(
            system_prompt=(
                "You are a general execution node. Complete the assigned task.\n"
                "Use [REF: artifact://...] for file content. Output ONLY JSON."
            ),
            user_prompt_template="{{input}}",
        ),
    }


ROLE_TEMPLATES = _build_role_templates()

# ============================================================
# 模式专用补充
# ============================================================

PATTERN_EXTRAS: dict[str, dict[str, str]] = {
    "fan_out_fan_in": {
        "dispatcher": (
            "\nFor fan-out: assign ONE task per downstream worker. "
            "Number each worker task clearly as [Worker1], [Worker2], etc."
        ),
        "aggregator": (
            "\nFor fan-in: list each worker's result before giving the final synthesis. "
            "Reference each result by worker ID."
        ),
    },
    "sequential": {
        "worker": (
            "\nThis is a sequential pipeline. Your input comes from the previous step. "
            "Process ONLY your step and pass the output forward. DO NOT skip steps."
        ),
    },
    "conditional": {
        "classifier_extra": (
            "\nYou are a classifier. Analyze the input and output ONLY the classification "
            "label (e.g., 'fact' or 'analysis'). DO NOT elaborate."
        ),
    },
    "cyclic": {
        "generator": (
            "\nGenerate content based on requirements. Output ONLY the content itself."
        ),
        "reflector": (
            "\nEvaluate the generated content quality. Reply SATISFIED if acceptable, "
            "or NEEDS_IMPROVEMENT: <reason> if not. DO NOT use any tools."
        ),
        "improver": (
            "\nImprove the content based on feedback. Output ONLY the improved version."
        ),
    },
}


# ============================================================
# PromptGenerator
# ============================================================

class PromptGenerator:
    """根据拓扑报告 + 任务描述，为每个节点生成角色匹配的 Prompt 和工具列表。"""

    def generate(self, report: TopologyReport, task_description: str,
                 node_configs: dict[str, dict]) -> PromptsResult:
        result = PromptsResult(
            topology={
                "pattern": report.pattern,
                "is_valid": report.is_valid,
                "warnings": report.warnings,
                "suggestions": report.suggestions,
                "node_roles": report.node_roles,
            }
        )

        # 找到 dispatcher（用于 worker 模板）
        dispatcher_id = None
        for nid, role in report.node_roles.items():
            if role == "dispatcher":
                dispatcher_id = nid
                break

        # 找到 aggregator 的上游 worker 节点
        aggregator_upstream: list[str] = []
        for nid, role in report.node_roles.items():
            if role == "aggregator":
                aggregator_upstream = [
                    uid for uid, r in report.node_roles.items()
                    if r in ("worker", "entry_worker", "leaf_worker")
                ]
                break

        # 统计 worker 数量，用于编号
        worker_ids = [nid for nid, r in report.node_roles.items() if r == "worker"]
        worker_index_map = {wid: i + 1 for i, wid in enumerate(worker_ids)}

        for nid, role in report.node_roles.items():
            base = ROLE_TEMPLATES.get(role, ROLE_TEMPLATES["unknown"])
            sp = base.system_prompt
            ut = base.user_prompt_template

            # 补充模式专用 prompt
            extras = PATTERN_EXTRAS.get(report.pattern, {})
            if role in extras:
                sp = sp + "\n" + extras[role] if sp else extras[role]

            # Worker 编号替换
            if role == "worker" and nid in worker_index_map:
                idx = worker_index_map[nid]
                sp = sp.replace("{worker_index}", str(idx))
                sp = sp.replace(f"[Worker{idx}]", f"[Worker{idx}]")

            # 动态模板替换
            if role == "worker" and dispatcher_id:
                idx = worker_index_map.get(nid, 0)
                sp = sp.replace("{worker_index}", str(idx))
                ut = (
                    f"Dispatcher Plan:\n{{{{{dispatcher_id}.output}}}}\n\n"
                    f"YOUR TASK: Find and complete ONLY the [Worker{idx}] task from the plan above."
                )
            elif role == "aggregator" and aggregator_upstream:
                parts = [f"{{{{{uid}.output}}}}" for uid in aggregator_upstream]
                ut = "\n".join(f"Worker {i+1} Result: {p}" for i, p in enumerate(parts))

            # Condition / Loop 不需要 prompt
            if role in ("router", "loop_controller"):
                sp = ""
                ut = ""

            # 注入 JSON 输出约束
            schema = OUTPUT_SCHEMAS.get(role, "")
            if schema and sp:
                sp = sp + "\n" + schema

            # 任务描述定制
            if task_description and sp:
                sp = sp.replace("user's request", task_description[:100])

            # 允许覆盖已有 config
            existing_config = node_configs.get(nid, {})
            if existing_config.get("system_prompt"):
                sp = existing_config["system_prompt"]
            if existing_config.get("user_prompt_template"):
                ut = existing_config["user_prompt_template"]

            # 工具分配
            tools = get_tools_for_role(role, task_description)

            result.prompts[nid] = NodePrompt(
                system_prompt=sp,
                user_prompt_template=ut,
                allowed_tools=tools,
                output_schema=schema,
            )

        return result


# ============================================================
# 便捷函数
# ============================================================

def generate_prompts(canvas_data: dict, task_description: str = "",
                     node_configs: dict[str, dict] | None = None) -> PromptsResult:
    """便捷函数: 分析拓扑 + 生成 Prompt。"""
    from .topology import analyze_topology
    report = analyze_topology(canvas_data)
    return PromptGenerator().generate(report, task_description,
                                      node_configs or {})


def generate_prompts_for_template(template_name: str, task_description: str = "") -> PromptsResult:
    """为内置模板生成 Prompt。"""
    from .templates import TEMPLATES
    tmpl = TEMPLATES.get(template_name)
    if not tmpl:
        raise ValueError(f"Unknown template: {template_name}")
    canvas = tmpl["canvas_data"]
    node_configs = {n["id"]: n.get("config", {}) for n in canvas["nodes"]}
    return generate_prompts(canvas, task_description, node_configs)
