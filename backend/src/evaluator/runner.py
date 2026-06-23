"""
FlowForge v0.1 - 评估运行器
批量运行测试集，收集 LLM-as-Judge 结果。
"""
import time
import asyncio
from typing import Any

import anthropic

from ..engine.executor import FlowExecutor
from ..evaluator.metrics import compute_metrics
from ..config import ANTHROPIC_BASE_URL, ANTHROPIC_API_KEY, ANTHROPIC_MODEL
from ..llm_utils import extract_text_from_response

_client: anthropic.Anthropic | None = None


def _get_judge_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(
            base_url=ANTHROPIC_BASE_URL,
            api_key=ANTHROPIC_API_KEY,
        )
    return _client


class EvaluationRunner:
    """评估运行器 —— 对架构在测试集上的表现进行批量评测。

    用法：
        runner = EvaluationRunner(canvas_data, test_cases)
        result = await runner.run()
        # result 包含 summary + details
    """

    def __init__(self, canvas_data: dict, test_cases: list[dict]):
        self.canvas = canvas_data
        self.test_cases = test_cases

    async def run(self) -> dict:
        """对每个 test case 执行架构并评估。"""
        details = []

        for tc in self.test_cases:
            question = tc.get("question", "")
            if not question:
                continue

            start = time.time()
            output = ""
            error = ""
            latency_ms = 0
            tokens = 0
            tool_calls = 0

            try:
                executor = FlowExecutor(self.canvas)
                exec_result = await executor.execute(question)

                output = exec_result.get("final_output", "")
                error = exec_result.get("error", "")
                latency_ms = exec_result.get("total_latency_ms", 0)
                tokens = exec_result.get("total_tokens", 0)
                tool_calls = exec_result.get("total_tool_calls", 0)

                # LLM-as-Judge
                if output and not error:
                    success = await self._judge(question, output, tc)
                else:
                    success = False

            except Exception as e:
                output = ""
                error = str(e)
                latency_ms = int((time.time() - start) * 1000)
                tokens = 0
                success = False

            details.append({
                "test_id": tc.get("id", 0),
                "question": question,
                "category": tc.get("category", ""),
                "success": success,
                "latency_ms": latency_ms,
                "tokens": tokens,
                "output": output[:1000],
                "error": error,
                "tool_calls": tool_calls,
                "tool_errors": 0,
                "tool_call_log": [],
            })

        # 计算汇总指标（使用 v0.2 扩展版 compute_metrics）
        summary = compute_metrics(details)
        return {
            "summary": summary,
            "details": details,
        }

    async def _judge(self, question: str, answer: str, test_case: dict) -> bool:
        """LLM-as-Judge + keyword matching。

        先用关键词检测，再交 LLM 复核。
        """
        notes = test_case.get("notes", "")
        expected_contains = test_case.get("expected_contains", [])

        # 关键词快速通过：只要答案包含任一预期关键词即视为候选正确
        keyword_match = False
        if expected_contains:
            answer_lower = answer.lower()
            keyword_match = any(kw.lower() in answer_lower for kw in expected_contains)

        # LLM 复核（简化 prompt）
        judge_prompt = (
            f"Task: {question[:500]}\n\n"
            f"Answer: {answer[:1500]}\n\n"
            f"Does the answer correctly solve the task? Reply YES or NO."
        )

        try:
            client = _get_judge_client()
            response = client.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=10,
                temperature=0.0,
                messages=[{"role": "user", "content": judge_prompt}],
            )
            judge_result = extract_text_from_response(response).strip().upper()
            llm_says_yes = "YES" in judge_result
            # 关键词匹配 + LLM 判断，任一通过即算成功
            return keyword_match or llm_says_yes
        except Exception:
            # LLM 调用失败，回退到关键词匹配
            return keyword_match
