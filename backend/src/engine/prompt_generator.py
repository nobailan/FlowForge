"""
FlowForge v0.4 - Prompt 自动生成引擎
根据拓扑分析结果，为每个节点生成角色匹配的 System Prompt。
"""
from dataclasses import dataclass, field
from .topology import TopologyReport


@dataclass
class NodePrompt:
    system_prompt: str = ""
    user_prompt_template: str = "{{input}}"


@dataclass
class PromptsResult:
    prompts: dict[str, NodePrompt] = field(default_factory=dict)
    topology: dict = field(default_factory=dict)


class PromptGenerator:
    """根据拓扑报告生成节点 Prompt。"""

    # 内置 Prompt 模板库
    TEMPLATES = {
        "dispatcher": NodePrompt(
            system_prompt=(
                "你是任务拆解者。将用户需求分解为独立的子任务，分派给下游执行者。"
                "你只负责拆解和分派，不执行任何任务。"
                "输出格式: [Worker1] 具体任务描述"
            ),
            user_prompt_template="{{input}}",
        ),
        "aggregator": NodePrompt(
            system_prompt=(
                "你是汇总者。综合上游执行者的输出，给用户一个完整、清晰的最终回答。"
                "不要重新执行任务，只做整合和总结。"
            ),
            user_prompt_template="",  # 由 generator 根据上游节点动态填充
        ),
        "worker": NodePrompt(
            system_prompt=(
                "你是执行者。只完成分配给你的任务，不要做其他执行者的工作。"
                "只输出结果，不输出分析和过程。"
            ),
            user_prompt_template="主管指令:\n{DISPATCHER_OUTPUT}",
        ),
        "entry_worker": NodePrompt(
            system_prompt=(
                "你是流程的起始节点。接收用户输入，完成第一步处理。"
                "只输出本步骤的结果，不要试图完成整个任务。"
            ),
            user_prompt_template="{{input}}",
        ),
        "leaf_worker": NodePrompt(
            system_prompt=(
                "你是流程的最终节点。汇总前面步骤的结果，输出最终答案。"
                "简洁清晰，不要添加额外信息。"
            ),
            user_prompt_template="",
        ),
        "coordinator": NodePrompt(
            system_prompt=(
                "你是协调者。接收上游输入，协调下游执行者完成任务。"
                "明确分配子任务，但不要自己执行。"
            ),
            user_prompt_template="{{input}}",
        ),
        "router": NodePrompt(
            system_prompt="",
            user_prompt_template="",
        ),
        "loop_controller": NodePrompt(
            system_prompt="",
            user_prompt_template="",
        ),
        "unknown": NodePrompt(
            system_prompt="你是通用执行节点。根据上下文完成任务。",
            user_prompt_template="{{input}}",
        ),
    }

    # 补充 prompt（特定模式专用）
    PATTERN_EXTRAS = {
        "fan_out_fan_in": {
            "dispatcher": (
                "输出格式: 为每个下游节点单独一行描述任务。"
            ),
            "aggregator": (
                "列出每个执行者的结果，然后给出综合结论。"
            ),
        },
        "sequential": {
            "worker": (
                "你是流水线中的一步。输入来自上一步，输出传给下一步。"
                "只做你这一步的工作，不要跳步。"
            ),
        },
        "conditional": {
            "classifier_extra": (
                "你是分类器。分析用户输入，只输出分类标签（如 fact 或 analysis）。"
            ),
        },
        "cyclic": {
            "generator": (
                "你是内容生成器。根据需求生成内容。只输出内容本身。"
            ),
            "reflector": (
                "你是质量评估器。只评价内容质量。满意回复 SATISFIED。"
                "不满意回复 NEEDS_IMPROVEMENT: 原因。不要使用任何工具。"
            ),
            "improver": (
                "你是改进者。根据反馈改进内容。只输出改进后的内容。"
            ),
        },
    }

    def generate(self, report: TopologyReport, task_description: str,
                 node_configs: dict[str, dict]) -> PromptsResult:
        """生成所有节点的 Prompt。"""
        result = PromptsResult(
            topology={
                "pattern": report.pattern,
                "is_valid": report.is_valid,
                "warnings": report.warnings,
                "suggestions": report.suggestions,
                "node_roles": report.node_roles,
            }
        )

        # 找到 dispatcher 节点（用于 worker 模板）
        dispatcher_id = None
        for nid, role in report.node_roles.items():
            if role == "dispatcher":
                dispatcher_id = nid
                break

        # 找到 aggregator 的上游节点
        aggregator_upstream = []
        for nid, role in report.node_roles.items():
            if role == "aggregator":
                aggregator_upstream = [
                    uid for uid, r in report.node_roles.items()
                    if r in ("worker", "entry_worker", "leaf_worker")
                ]
                break

        for nid, role in report.node_roles.items():
            base = self.TEMPLATES.get(role, self.TEMPLATES["unknown"])
            sp = base.system_prompt
            ut = base.user_prompt_template

            # 补充模式专用 prompt
            extras = self.PATTERN_EXTRAS.get(report.pattern, {})
            if role in extras:
                sp = sp + " " + extras[role] if sp else extras[role]

            # 动态替换
            if role == "worker" and dispatcher_id:
                ut = f"主管指令:\n{{{{{dispatcher_id}.output}}}}"
            elif role == "aggregator" and aggregator_upstream:
                parts = [f"{{{{{uid}.output}}}}" for uid in aggregator_upstream]
                ut = "\n".join(f"执行者 {i+1} 结果: {p}" for i, p in enumerate(parts))

            # Condition/Loop 节点不需要 prompt
            if role in ("router", "loop_controller"):
                sp = ""
                ut = ""

            # 用任务描述定制
            if task_description and sp:
                sp = sp.replace("用户需求", task_description[:100])

            # 允许覆盖已有 config
            existing_config = node_configs.get(nid, {})
            if existing_config.get("system_prompt"):
                sp = existing_config["system_prompt"]
            if existing_config.get("user_prompt_template"):
                ut = existing_config["user_prompt_template"]

            result.prompts[nid] = NodePrompt(system_prompt=sp, user_prompt_template=ut)

        return result


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
