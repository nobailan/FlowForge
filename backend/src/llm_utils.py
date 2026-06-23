"""
FlowForge v0.1 - LLM 工具函数
处理 DeepSeek Anthropic-compatible API 的响应提取。
"""
from anthropic.types import Message


def extract_text_from_response(response: Message) -> str:
    """从 Anthropic SDK 响应中提取文本。

    处理 DeepSeek 的 ThinkingBlock + TextBlock 结构，
    只拼接 TextBlock 的文本。
    """
    text_parts = []
    for block in response.content:
        if hasattr(block, "text"):
            text_parts.append(block.text)
    return "".join(text_parts)


def get_text_blocks(response: Message) -> list[str]:
    """获取响应中所有 TextBlock 的文本列表。"""
    return [block.text for block in response.content if hasattr(block, "text")]
