"""
FlowForge v0.5 - 内置模板
Token 优化版：英文 JSON 约束 + 工具按需分配 + 短 max_steps。
"""
TEMPLATES: dict[str, dict] = {
    # ================================================================
    # 1. Supervisor-Worker
    # ================================================================
    "supervisor_worker": {
        "name": "supervisor_worker",
        "display_name": "Supervisor-Worker",
        "description": "主管 Agent 拆解任务分发给多个 Worker，汇总结果",
        "canvas_data": {
            "nodes": [
                {"id": "supervisor", "type": "llm", "label": "Supervisor",
                 "config": {"model_provider": "deepseek", "model_id": "deepseek-v4-pro",
                            "opencode_agent": "build", "max_steps": 5, "timeout_seconds": 60,
                            "allowed_tools": [],  # dispatcher: no tools
                            "system_prompt": (
                                "You are a Task Dispatcher. Decompose the user's request into 3 independent subtasks.\n"
                                "DO NOT execute any task yourself. DO NOT use any tools.\n"
                                "OUTPUT FORMAT (MANDATORY):\n"
                                '{"plan": [{"worker_id": "worker_1", "task": "..."}, '
                                '{"worker_id": "worker_2", "task": "..."}, '
                                '{"worker_id": "worker_3", "task": "..."}]}\n'
                                "Output ONLY this JSON. No markdown, no explanation."
                            ),
                            "user_prompt_template": "{{input}}"},
                 "position": {"x": 400, "y": 50}},
                {"id": "worker_1", "type": "llm", "label": "Worker 1",
                 "config": {"model_provider": "deepseek", "model_id": "deepseek-v4-pro",
                            "opencode_agent": "build", "max_steps": 8, "timeout_seconds": 90,
                            "allowed_tools": ["read", "grep", "glob"],
                            "system_prompt": (
                                "You are Worker 1. Do ONLY the [Worker 1] task from the dispatcher plan.\n"
                                "DO NOT do other workers' tasks. DO NOT create a report.\n"
                                "Use [REF: artifact://key] to reference files instead of copying content.\n"
                                "OUTPUT FORMAT (MANDATORY):\n"
                                '{"status": "ok"|"error", "result": "<concise result, max 300 chars>", '
                                '"refs": ["artifact://..."], "insights": []}\n'
                                "Output ONLY this JSON."
                            ),
                            "user_prompt_template": "Dispatcher Plan:\n{{supervisor.output}}\n\nYOUR TASK: Find and complete ONLY the [Worker 1] task from the plan above."},
                 "position": {"x": 100, "y": 250}},
                {"id": "worker_2", "type": "llm", "label": "Worker 2",
                 "config": {"model_provider": "deepseek", "model_id": "deepseek-v4-pro",
                            "opencode_agent": "build", "max_steps": 8, "timeout_seconds": 90,
                            "allowed_tools": ["read", "grep", "glob"],
                            "system_prompt": (
                                "You are Worker 2. Do ONLY the [Worker 2] task from the dispatcher plan.\n"
                                "DO NOT do other workers' tasks. DO NOT create a report.\n"
                                "Use [REF: artifact://key] to reference files instead of copying content.\n"
                                "OUTPUT FORMAT (MANDATORY):\n"
                                '{"status": "ok"|"error", "result": "<concise result, max 300 chars>", '
                                '"refs": ["artifact://..."], "insights": []}\n'
                                "Output ONLY this JSON."
                            ),
                            "user_prompt_template": "Dispatcher Plan:\n{{supervisor.output}}\n\nYOUR TASK: Find and complete ONLY the [Worker 2] task from the plan above."},
                 "position": {"x": 400, "y": 250}},
                {"id": "worker_3", "type": "tool", "label": "Worker 3 (Tool)",
                 "config": {"model_provider": "deepseek", "model_id": "deepseek-v4-pro",
                            "timeout_seconds": 90,
                            "allowed_tools": ["read", "bash"],
                            "tool_task": (
                                "Dispatcher Plan:\n{{supervisor.output}}\n\n"
                                "YOUR TASK: Find and complete ONLY the [Worker 3] task from the plan above.\n"
                                "OUTPUT: {\"status\": \"ok\"|\"error\", \"result\": \"<concise>\"}"
                            )},
                 "position": {"x": 700, "y": 250}},
                {"id": "aggregator", "type": "llm", "label": "Aggregator",
                 "config": {"model_provider": "deepseek", "model_id": "deepseek-v4-pro",
                            "opencode_agent": "build", "max_steps": 5, "timeout_seconds": 60,
                            "allowed_tools": [],  # aggregator: no tools
                            "system_prompt": (
                                "You are a Result Aggregator. Synthesize all worker outputs into "
                                "ONE comprehensive final answer.\n"
                                "DO NOT re-execute any task. DO NOT use any tools.\n"
                                "OUTPUT FORMAT (MANDATORY):\n"
                                '{"answer": "<final answer>", "sources": [{"ref": "artifact://...", "relevance": "..."}], "confidence": 0.0-1.0}\n'
                                "Output ONLY this JSON."
                            ),
                            "user_prompt_template": "Worker 1 Result: {{worker_1.output}}\nWorker 2 Result: {{worker_2.output}}\nWorker 3 Result: {{worker_3.output}}"},
                 "position": {"x": 400, "y": 450}},
            ],
            "edges": [
                {"source": "supervisor", "target": "worker_1"},
                {"source": "supervisor", "target": "worker_2"},
                {"source": "supervisor", "target": "worker_3"},
                {"source": "worker_1", "target": "aggregator"},
                {"source": "worker_2", "target": "aggregator"},
                {"source": "worker_3", "target": "aggregator"},
            ],
        },
    },

    # ================================================================
    # 2. Sequential Chain
    # ================================================================
    "sequential_chain": {
        "name": "sequential_chain",
        "display_name": "Sequential Chain",
        "description": "节点串行执行，每步只做分内事，输出传递到下一步",
        "canvas_data": {
            "nodes": [
                {"id": "step_1", "type": "llm", "label": "Step 1: Analyze",
                 "config": {"model_provider": "deepseek", "model_id": "deepseek-v4-pro",
                            "opencode_agent": "build", "max_steps": 5, "timeout_seconds": 60,
                            "allowed_tools": ["read", "grep", "glob"],
                            "system_prompt": (
                                "You are Step 1 ONLY. Process the user input and produce a structured result.\n"
                                "DO NOT do other steps' work. DO NOT generate a report.\n"
                                "OUTPUT FORMAT (MANDATORY):\n"
                                '{"status": "ok"|"error", "result": "<concise>", "refs": []}\n'
                                "Output ONLY this JSON."
                            ),
                            "user_prompt_template": "{{input}}"},
                 "position": {"x": 400, "y": 50}},
                {"id": "step_2", "type": "llm", "label": "Step 2: Reason",
                 "config": {"model_provider": "deepseek", "model_id": "deepseek-v4-pro",
                            "opencode_agent": "build", "max_steps": 5, "timeout_seconds": 60,
                            "allowed_tools": ["read", "grep", "glob"],
                            "system_prompt": (
                                "You are Step 2 ONLY. Take Step 1's result and perform your analysis.\n"
                                "DO NOT do step 1 or step 3's work.\n"
                                "OUTPUT FORMAT (MANDATORY):\n"
                                '{"status": "ok"|"error", "result": "<concise>", "insights": []}\n'
                                "Output ONLY this JSON."
                            ),
                            "user_prompt_template": "Step 1 output:\n{{step_1.output}}"},
                 "position": {"x": 400, "y": 200}},
                {"id": "step_3", "type": "tool", "label": "Step 3: Execute",
                 "config": {"model_provider": "deepseek", "model_id": "deepseek-v4-pro",
                            "timeout_seconds": 60,
                            "allowed_tools": ["bash", "read"],
                            "tool_task": (
                                "Step 2 result:\n{{step_2.output}}\n\n"
                                "You are Step 3 ONLY. Execute the required action.\n"
                                "OUTPUT: {\"status\": \"ok\"|\"error\", \"result\": \"<concise>\"}"
                            )},
                 "position": {"x": 400, "y": 350}},
                {"id": "step_4", "type": "llm", "label": "Step 4: Summarize",
                 "config": {"model_provider": "deepseek", "model_id": "deepseek-v4-pro",
                            "opencode_agent": "build", "max_steps": 5, "timeout_seconds": 60,
                            "allowed_tools": [],
                            "system_prompt": (
                                "You are Step 4 ONLY. Combine previous steps' results into ONE final answer.\n"
                                "Be concise. DO NOT redo previous work. DO NOT use tools.\n"
                                "OUTPUT FORMAT (MANDATORY):\n"
                                '{"answer": "<final answer>", "confidence": 0.0-1.0}\n'
                                "Output ONLY this JSON."
                            ),
                            "user_prompt_template": "Step 1: {{step_1.output}}\nStep 2: {{step_2.output}}\nStep 3: {{step_3.output}}"},
                 "position": {"x": 400, "y": 500}},
            ],
            "edges": [
                {"source": "step_1", "target": "step_2"},
                {"source": "step_2", "target": "step_3"},
                {"source": "step_3", "target": "step_4"},
            ],
        },
    },

    # ================================================================
    # 3. Parallel Experts
    # ================================================================
    "parallel": {
        "name": "parallel",
        "display_name": "Parallel Experts",
        "description": "3个专家同时独立分析同一问题后汇总",
        "canvas_data": {
            "nodes": [
                {"id": "fan_out", "type": "llm", "label": "Fan-Out",
                 "config": {"model_provider": "deepseek", "model_id": "deepseek-v4-pro",
                            "opencode_agent": "build", "max_steps": 1, "timeout_seconds": 15,
                            "system_prompt": "Output the single word: READY",
                            "user_prompt_template": "READY"},
                 "position": {"x": 400, "y": 50}},
                {"id": "expert_a", "type": "llm", "label": "Expert A: Facts",
                 "config": {"model_provider": "deepseek", "model_id": "deepseek-v4-pro",
                            "opencode_agent": "build", "max_steps": 8, "timeout_seconds": 90,
                            "allowed_tools": ["read", "grep"],
                            "system_prompt": (
                                "You are Expert A (Facts). Answer from a factual, data-driven perspective.\n"
                                "Be concise. DO NOT do other experts' work.\n"
                                "OUTPUT: {\"status\": \"ok\"|\"error\", \"result\": \"<concise>\", \"perspective\": \"factual\"}"
                            ),
                            "user_prompt_template": "{{input}}"},
                 "position": {"x": 100, "y": 250}},
                {"id": "expert_b", "type": "llm", "label": "Expert B: Logic",
                 "config": {"model_provider": "deepseek", "model_id": "deepseek-v4-pro",
                            "opencode_agent": "build", "max_steps": 8, "timeout_seconds": 90,
                            "allowed_tools": ["read"],
                            "system_prompt": (
                                "You are Expert B (Logic). Answer from a logical reasoning perspective.\n"
                                "Be concise. DO NOT do other experts' work.\n"
                                "OUTPUT: {\"status\": \"ok\"|\"error\", \"result\": \"<concise>\", \"perspective\": \"logical\"}"
                            ),
                            "user_prompt_template": "{{input}}"},
                 "position": {"x": 400, "y": 250}},
                {"id": "expert_c", "type": "tool", "label": "Expert C: Tools",
                 "config": {"model_provider": "deepseek", "model_id": "deepseek-v4-pro",
                            "timeout_seconds": 60,
                            "allowed_tools": ["bash", "read"],
                            "tool_task": (
                                "{{input}}\n\n"
                                "Answer from a practical/tools perspective. Output ONLY the JSON:\n"
                                '{"status": "ok"|"error", "result": "<concise>"}'
                            )},
                 "position": {"x": 700, "y": 250}},
                {"id": "merger", "type": "llm", "label": "Merger",
                 "config": {"model_provider": "deepseek", "model_id": "deepseek-v4-pro",
                            "opencode_agent": "build", "max_steps": 8, "timeout_seconds": 90,
                            "allowed_tools": [],
                            "system_prompt": (
                                "Synthesize the three expert opinions into ONE cohesive final answer.\n"
                                "DO NOT add new analysis. DO NOT use tools.\n"
                                "OUTPUT: {\"answer\": \"<final>\", \"confidence\": 0.0-1.0, \"best_perspective\": \"factual|logical|practical\"}"
                            ),
                            "user_prompt_template": "Expert A: {{expert_a.output}}\nExpert B: {{expert_b.output}}\nExpert C: {{expert_c.output}}"},
                 "position": {"x": 400, "y": 450}},
            ],
            "edges": [
                {"source": "fan_out", "target": "expert_a"},
                {"source": "fan_out", "target": "expert_b"},
                {"source": "fan_out", "target": "expert_c"},
                {"source": "expert_a", "target": "merger"},
                {"source": "expert_b", "target": "merger"},
                {"source": "expert_c", "target": "merger"},
            ],
        },
    },

    # ================================================================
    # 4. Conditional Branch
    # ================================================================
    "conditional_branch": {
        "name": "conditional_branch",
        "display_name": "Conditional Branch",
        "description": "根据条件判断走不同分支，最终汇总",
        "canvas_data": {
            "nodes": [
                {"id": "classifier", "type": "llm", "label": "Classifier",
                 "config": {"model_provider": "deepseek", "model_id": "deepseek-v4-pro",
                            "opencode_agent": "build", "max_steps": 3, "timeout_seconds": 30,
                            "allowed_tools": [],
                            "system_prompt": (
                                "Classify the input. Output ONLY the single word 'fact' or 'analysis'.\n"
                                "DO NOT explain. DO NOT use tools."
                            ),
                            "user_prompt_template": "{{input}}"},
                 "position": {"x": 400, "y": 50}},
                {"id": "condition_check", "type": "condition", "label": "Type?",
                 "config": {"field": "classifier.output", "operator": "contains", "value": "analysis"},
                 "position": {"x": 400, "y": 200}},
                {"id": "fact_handler", "type": "tool", "label": "Fact Lookup",
                 "config": {"model_provider": "deepseek", "model_id": "deepseek-v4-pro",
                            "timeout_seconds": 30,
                            "allowed_tools": ["read"],
                            "tool_task": (
                                "Look up the factual answer for:\n{{input}}\n\n"
                                "Output ONLY: {\"status\": \"ok\"|\"error\", \"result\": \"<concise>\"}"
                            )},
                 "position": {"x": 150, "y": 350}},
                {"id": "analysis_handler", "type": "llm", "label": "Deep Analysis",
                 "config": {"model_provider": "deepseek", "model_id": "deepseek-v4-pro",
                            "opencode_agent": "build", "max_steps": 8, "timeout_seconds": 90,
                            "allowed_tools": ["read", "grep", "glob"],
                            "system_prompt": (
                                "Provide a deep analysis of the input. Be thorough but concise.\n"
                                "Use [REF: artifact://key] for file references.\n"
                                "OUTPUT: {\"status\": \"ok\"|\"error\", \"result\": \"<analysis>\", \"refs\": []}"
                            ),
                            "user_prompt_template": "{{input}}"},
                 "position": {"x": 650, "y": 350}},
                {"id": "finalizer", "type": "llm", "label": "Finalizer",
                 "config": {"model_provider": "deepseek", "model_id": "deepseek-v4-pro",
                            "opencode_agent": "build", "max_steps": 5, "timeout_seconds": 60,
                            "allowed_tools": [],
                            "system_prompt": (
                                "Produce the final answer based on the handler output.\n"
                                "DO NOT redo work. DO NOT use tools.\n"
                                "OUTPUT: {\"answer\": \"<final>\", \"confidence\": 0.0-1.0}"
                            ),
                            "user_prompt_template": "Handler output: {{fact_handler.output}}{{analysis_handler.output}}"},
                 "position": {"x": 400, "y": 500}},
            ],
            "edges": [
                {"source": "classifier", "target": "condition_check"},
                {"source": "condition_check", "target": "analysis_handler", "label": "true"},
                {"source": "condition_check", "target": "fact_handler", "label": "false"},
                {"source": "fact_handler", "target": "finalizer"},
                {"source": "analysis_handler", "target": "finalizer"},
            ],
        },
    },

    # ================================================================
    # 5. Reflection Loop
    # ================================================================
    "reflection_loop": {
        "name": "reflection_loop",
        "display_name": "Reflection Loop",
        "description": "生成回答 → 反思 → 不满足则改进并重试，满足则退出",
        "canvas_data": {
            "nodes": [
                {"id": "generator", "type": "llm", "label": "Generator",
                 "config": {"model_provider": "deepseek", "model_id": "deepseek-v4-pro",
                            "opencode_agent": "build", "max_steps": 5, "timeout_seconds": 60,
                            "allowed_tools": [],
                            "system_prompt": (
                                "Generate an answer to the input. DO NOT use any tools.\n"
                                "Output ONLY the answer text. No markdown, no explanation.\n"
                                "If you see an improvement suggestion, incorporate it and output the improved version."
                            ),
                            "user_prompt_template": "{{input}}{{improver.output}}"},
                 "position": {"x": 400, "y": 50}},
                {"id": "reflector", "type": "llm", "label": "Reflector",
                 "config": {"model_provider": "deepseek", "model_id": "deepseek-v4-pro",
                            "opencode_agent": "build", "max_steps": 3, "timeout_seconds": 30,
                            "allowed_tools": [],
                            "system_prompt": (
                                "You are a quality evaluator. DO NOT use any tools.\n"
                                "Evaluate the answer below for correctness and completeness.\n"
                                "Output ONLY 'SATISFIED' if the answer is good.\n"
                                "Output ONLY 'NEEDS_IMPROVEMENT: <specific reason>' if not.\n"
                                "DO NOT output anything else."
                            ),
                            "user_prompt_template": "Evaluate this answer:\n{{generator.output}}"},
                 "position": {"x": 400, "y": 200}},
                {"id": "quality_check", "type": "condition", "label": "Satisfied?",
                 "config": {"field": "reflector.output", "operator": "contains", "value": "SATISFIED"},
                 "position": {"x": 400, "y": 350}},
                {"id": "improver", "type": "llm", "label": "Improver",
                 "config": {"model_provider": "deepseek", "model_id": "deepseek-v4-pro",
                            "opencode_agent": "build", "max_steps": 5, "timeout_seconds": 60,
                            "allowed_tools": [],
                            "system_prompt": (
                                "Improve the answer based on the feedback. DO NOT use any tools.\n"
                                "Output ONLY the improved answer text. No explanation."
                            ),
                            "user_prompt_template": "Original:\n{{generator.output}}\n\nFeedback:\n{{reflector.output}}\n\nImproved version:"},
                 "position": {"x": 400, "y": 500}},
            ],
            "edges": [
                {"source": "generator", "target": "reflector"},
                {"source": "reflector", "target": "quality_check"},
                {"source": "quality_check", "target": "improver", "label": "false"},
                {"source": "improver", "target": "generator"},
            ],
        },
    },
}


def get_template(name: str) -> dict | None:
    return TEMPLATES.get(name)


def list_templates() -> list[dict]:
    return [
        {
            "name": t["name"],
            "display_name": t["display_name"],
            "description": t["description"],
            "node_count": len(t["canvas_data"]["nodes"]),
            "edge_count": len(t["canvas_data"]["edges"]),
        }
        for t in TEMPLATES.values()
    ]
