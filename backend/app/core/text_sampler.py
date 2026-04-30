"""
文本采样工具

替代粗暴的 content[:8000] 截断，提供均匀分布的文本采样
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def sample_text(content: str, max_chars: int = 8000, strategy: str = "spread") -> str:
    """
    从长文本中采样指定长度的片段。

    Args:
        content: 完整文本
        max_chars: 最大字符数
        strategy: 采样策略
            - "spread": 均匀分布采样（默认），覆盖全文
            - "head": 只取开头（最简单，适合需要顺序信息的场景）
            - "head_tail": 取开头和结尾各一半

    Returns:
        采样后的文本
    """
    if len(content) <= max_chars:
        return content

    if strategy == "head":
        return content[:max_chars]

    if strategy == "head_tail":
        half = max_chars // 2
        return content[:half] + "\n\n...(省略中间部分)...\n\n" + content[-half:]

    # spread: 均匀分布采样
    # 将文本大致按 max_chars 分成若干段，从每段取一部分
    total_len = len(content)
    num_segments = max(1, total_len // max_chars)
    segment_size = max_chars // num_segments

    parts = []
    for i in range(num_segments):
        start = i * (total_len // num_segments)
        end = start + segment_size
        parts.append(content[start:end])

    result = "\n\n...(省略)...\n\n".join(parts)

    # 如果超出预算，截断到最后
    if len(result) > max_chars:
        result = result[:max_chars]

    return result
