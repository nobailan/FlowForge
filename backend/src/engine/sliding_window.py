"""
FlowForge v0.5 - 滑动窗口（Sliding Window）
第四刀：裁剪对话历史，只保留任务目标 + 最近 K 轮。
"""
from typing import Optional


class SlidingWindow:
    """滑动窗口消息裁剪器。

    策略：
    - 始终保留首条消息（任务目标），除非 max_turns 为 0
    - 保留最近 max_turns 轮对话
    - 中间被丢弃的消息插入一句摘要提示
    """

    def __init__(self, max_turns: int = 5, preserve_first: bool = True):
        self.max_turns = max_turns
        self.preserve_first = preserve_first

    def trim(self, messages: list[dict], task_goal: str = "") -> list[dict]:
        """裁剪消息列表到滑动窗口大小。

        Args:
            messages: 消息列表，每项为 {"role": "...", "content": "..."} 或字符串
            task_goal: 任务目标（如果 preserve_first=True，会被注入到保留的消息头）

        Returns:
            裁剪后的消息列表
        """
        if len(messages) <= self.max_turns + 1:
            return list(messages)

        omitted_count = len(messages) - self.max_turns - (1 if self.preserve_first else 0)
        if omitted_count <= 0:
            return list(messages)

        # 保留首条（任务目标）
        head = []
        if self.preserve_first and messages:
            head = [messages[0]]

        # 保留最近 K 轮
        tail = messages[-self.max_turns:]

        # 中间插入摘要标记
        summary = {
            "role": "system",
            "content": (
                f"[CONTEXT TRIMMED: {omitted_count} earlier turns omitted by sliding window. "
                f"Task goal: {task_goal[:200] if task_goal else 'see first message'}]"
            ),
        }

        return head + [summary] + tail

    def trim_text(self, text: str, max_chars: int = 8000,
                  keep_first_pct: float = 0.1) -> str:
        """对纯文本消息做裁剪（用于不支持结构化消息的场景）。

        策略：保留开头 10% + 结尾部分，中间截断。
        """
        if len(text) <= max_chars:
            return text

        keep_head = int(max_chars * keep_first_pct)
        keep_tail = max_chars - keep_head - 100  # 100 给分割线

        head = text[:keep_head]
        tail = text[-keep_tail:]

        # 在自然断点处切割
        last_nl = head.rfind("\n")
        if last_nl > keep_head * 0.5:
            head = head[:last_nl]

        first_nl = tail.find("\n")
        if first_nl != -1 and first_nl < len(tail) * 0.3:
            tail = tail[first_nl:]

        omitted = len(text) - len(head) - len(tail)
        return (
            head
            + f"\n\n[... {omitted} characters omitted by sliding window ...]\n\n"
            + tail
        )


# 窗口大小推荐
WINDOW_SIZES: dict[str, int] = {
    "llm": 5,           # 通用 agent，中等窗口
    "tool": 3,          # 工具调用，短窗口
    "retriever": 3,     # 检索，短窗口
    "subagent": 5,      # 子 agent，中等窗口
    "condition": 1,     # 条件路由，最小窗口
    "loop": 8,          # 循环，需要更多上下文
}


def get_window_size(node_type: str, node_config: Optional[dict] = None) -> int:
    """根据节点类型获取推荐窗口大小。"""
    if node_config and "max_turns" in node_config:
        return node_config["max_turns"]
    return WINDOW_SIZES.get(node_type, 5)
