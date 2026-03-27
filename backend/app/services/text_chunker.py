"""
文本分块服务

提供统一的文本分段能力，支持：
1. 智能段落分割（保持语义完整性）
2. 滑动窗口（可选重叠）
3. 章节感知分割
4. 句子优先分割
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Generator
import re
import logging

logger = logging.getLogger(__name__)


class ChunkStrategy(Enum):
    """分块策略"""
    PARAGRAPH = "paragraph"      # 段落优先
    CHAPTER = "chapter"          # 章节优先
    SLIDING_WINDOW = "sliding"   # 滑动窗口
    SENTENCE = "sentence"        # 句子优先


@dataclass
class ChunkConfig:
    """分块配置"""
    max_chunk_size: int = 2000
    overlap_size: int = 200      # 滑动窗口重叠大小
    min_chunk_size: int = 100    # 最小块大小
    strategy: ChunkStrategy = ChunkStrategy.PARAGRAPH
    keep_separator: bool = True  # 保留分隔符
    respect_sentence_boundary: bool = True  # 尊重句子边界


@dataclass
class TextChunk:
    """文本块"""
    content: str
    index: int
    start_char: int
    end_char: int
    chapter_num: Optional[int] = None
    chapter_title: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    @property
    def length(self) -> int:
        return len(self.content)


@dataclass
class ChunkResult:
    """分块结果"""
    chunks: List[TextChunk]
    total_chunks: int
    total_chars: int
    avg_chunk_size: float
    strategy_used: ChunkStrategy


class TextChunker:
    """文本分块器"""

    # 中文章节标题模式
    CHAPTER_PATTERNS = [
        re.compile(r'^第([一二三四五六七八九十百千\d]+)章\s*(.*)'),
        re.compile(r'^第([一二三四五六七八九十百千\d]+)节\s*(.*)'),
        re.compile(r'^[Cc]hapter\s*(\d+)\s*(.*)', re.IGNORECASE),
    ]

    # 中文句子结束符
    SENTENCE_ENDINGS = re.compile(r'[。！？…」』\n]')

    # 中文数字转换映射
    CHINESE_NUM_MAP = {
        '零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
        '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
        '十': 10, '百': 100, '千': 1000,
    }

    def __init__(self, config: ChunkConfig = None):
        self.config = config or ChunkConfig()

    def chunk(self, text: str, config: ChunkConfig = None) -> ChunkResult:
        """
        分块文本

        Args:
            text: 原始文本
            config: 分块配置（可选，覆盖默认配置）

        Returns:
            ChunkResult
        """
        cfg = config or self.config

        if not text or not text.strip():
            return ChunkResult(
                chunks=[],
                total_chunks=0,
                total_chars=0,
                avg_chunk_size=0,
                strategy_used=cfg.strategy
            )

        if cfg.strategy == ChunkStrategy.PARAGRAPH:
            chunks = self._chunk_by_paragraph(text, cfg)
        elif cfg.strategy == ChunkStrategy.SLIDING_WINDOW:
            chunks = self._chunk_by_sliding_window(text, cfg)
        elif cfg.strategy == ChunkStrategy.SENTENCE:
            chunks = self._chunk_by_sentence(text, cfg)
        elif cfg.strategy == ChunkStrategy.CHAPTER:
            chunks = self._chunk_by_chapter(text, cfg)
        else:
            chunks = self._chunk_by_paragraph(text, cfg)

        # 更新索引
        for i, chunk in enumerate(chunks):
            chunk.index = i

        total_chars = len(text)
        avg_size = sum(c.length for c in chunks) / len(chunks) if chunks else 0

        logger.info(
            f"文本分块完成: {len(chunks)} 个块, "
            f"策略={cfg.strategy.value}, "
            f"平均大小={avg_size:.0f}"
        )

        return ChunkResult(
            chunks=chunks,
            total_chunks=len(chunks),
            total_chars=total_chars,
            avg_chunk_size=avg_size,
            strategy_used=cfg.strategy
        )

    def _chunk_by_paragraph(self, text: str, config: ChunkConfig) -> List[TextChunk]:
        """按段落分块，保持段落完整性"""
        # 按段落分割（双换行或多个换行）
        paragraphs = re.split(r'\n\s*\n', text)

        chunks = []
        current_content = ""
        current_start = 0
        char_position = 0
        current_chapter = None
        current_chapter_title = None

        for para in paragraphs:
            para = para.strip()
            if not para:
                char_position += 2  # 跳过空行
                continue

            # 检查是否是章节标题
            chapter_info = self._detect_chapter(para)
            if chapter_info:
                current_chapter = chapter_info[0]
                current_chapter_title = chapter_info[1]

            # 判断是否需要开始新块
            if len(current_content) + len(para) + 2 > config.max_chunk_size:
                if current_content and len(current_content) >= config.min_chunk_size:
                    # 保存当前块
                    chunks.append(TextChunk(
                        content=current_content.strip(),
                        index=0,  # 后续更新
                        start_char=current_start,
                        end_char=char_position,
                        chapter_num=current_chapter,
                        chapter_title=current_chapter_title
                    ))
                    current_start = char_position
                    current_content = para
                else:
                    # 当前块太小，继续添加
                    current_content += ("\n\n" if current_content else "") + para
            else:
                current_content += ("\n\n" if current_content else "") + para

            char_position += len(para) + 2

        # 添加最后一个块
        if current_content and len(current_content) >= config.min_chunk_size:
            chunks.append(TextChunk(
                content=current_content.strip(),
                index=0,
                start_char=current_start,
                end_char=char_position,
                chapter_num=current_chapter,
                chapter_title=current_chapter_title
            ))
        elif chunks and current_content:
            # 最后一个小块合并到前一个块
            chunks[-1].content += "\n\n" + current_content
            chunks[-1].end_char = char_position

        return chunks

    def _chunk_by_sliding_window(self, text: str, config: ChunkConfig) -> List[TextChunk]:
        """滑动窗口分块，支持重叠"""
        chunks = []
        start = 0
        text_len = len(text)
        chunk_index = 0

        while start < text_len:
            # 计算当前窗口的结束位置
            end = min(start + config.max_chunk_size, text_len)

            # 如果不是最后一块，尝试在句子边界处断开
            if end < text_len and config.respect_sentence_boundary:
                # 在结束位置附近寻找句子边界
                search_start = max(start + config.max_chunk_size - 200, start)
                search_text = text[search_start:end + 100]

                # 找最后一个句子结束符
                matches = list(self.SENTENCE_ENDINGS.finditer(search_text))
                if matches:
                    last_match = matches[-1]
                    end = search_start + last_match.end()

            chunk_content = text[start:end].strip()
            if chunk_content:
                # 检测章节信息
                chapter_info = self._detect_chapter(chunk_content[:100])

                chunks.append(TextChunk(
                    content=chunk_content,
                    index=chunk_index,
                    start_char=start,
                    end_char=end,
                    chapter_num=chapter_info[0] if chapter_info else None,
                    chapter_title=chapter_info[1] if chapter_info else None,
                    metadata={'overlap_with_previous': start > 0}
                ))
                chunk_index += 1

            # 移动到下一个窗口（考虑重叠）
            step = config.max_chunk_size - config.overlap_size
            start += step

        return chunks

    def _chunk_by_sentence(self, text: str, config: ChunkConfig) -> List[TextChunk]:
        """按句子分块"""
        # 按句子分割
        sentences = self.SENTENCE_ENDINGS.split(text)

        chunks = []
        current_content = ""
        current_start = 0
        char_position = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            if len(current_content) + len(sentence) + 1 > config.max_chunk_size:
                if current_content:
                    chunks.append(TextChunk(
                        content=current_content.strip(),
                        index=0,
                        start_char=current_start,
                        end_char=char_position
                    ))
                    current_start = char_position
                    current_content = sentence
                else:
                    # 单个句子就超过限制，强制截断
                    chunks.append(TextChunk(
                        content=sentence[:config.max_chunk_size],
                        index=0,
                        start_char=current_start,
                        end_char=current_start + config.max_chunk_size
                    ))
                    current_start = char_position + config.max_chunk_size
                    current_content = ""
            else:
                current_content += (" " if current_content else "") + sentence

            char_position += len(sentence) + 1

        if current_content:
            chunks.append(TextChunk(
                content=current_content.strip(),
                index=0,
                start_char=current_start,
                end_char=char_position
            ))

        return chunks

    def _chunk_by_chapter(self, text: str, config: ChunkConfig) -> List[TextChunk]:
        """按章节分块，如果单章太长则进一步分割"""
        # 首先按章节分割
        chapter_positions = []
        for match in re.finditer(r'^第[一二三四五六七八九十百千\d]+章', text, re.MULTILINE):
            chapter_positions.append(match.start())

        # 如果没有找到章节标记，退回到段落分割
        if not chapter_positions:
            return self._chunk_by_paragraph(text, config)

        # 添加文本末尾位置
        chapter_positions.append(len(text))

        chunks = []
        for i, start in enumerate(chapter_positions[:-1]):
            end = chapter_positions[i + 1]
            chapter_text = text[start:end].strip()

            # 检测章节信息
            chapter_info = self._detect_chapter(chapter_text[:100])

            # 如果章节太长，进一步分割
            if len(chapter_text) > config.max_chunk_size:
                sub_chunks = self._chunk_by_paragraph(chapter_text, config)
                for sub in sub_chunks:
                    sub.chapter_num = chapter_info[0] if chapter_info else i + 1
                    sub.chapter_title = chapter_info[1] if chapter_info else None
                    sub.start_char += start
                    sub.end_char += start
                    chunks.append(sub)
            else:
                chunks.append(TextChunk(
                    content=chapter_text,
                    index=0,
                    start_char=start,
                    end_char=end,
                    chapter_num=chapter_info[0] if chapter_info else i + 1,
                    chapter_title=chapter_info[1] if chapter_info else None
                ))

        return chunks

    def _detect_chapter(self, text: str) -> Optional[tuple]:
        """
        检测章节信息

        Returns:
            (章节号, 章节标题) 或 None
        """
        for pattern in self.CHAPTER_PATTERNS:
            match = pattern.match(text)
            if match:
                num_str = match.group(1)
                title = match.group(2).strip() if len(match.groups()) > 1 else ""

                # 转换章节号
                chapter_num = self._chinese_to_int(num_str)
                if chapter_num is not None:
                    return (chapter_num, title if title else f"第{chapter_num}章")

        return None

    def _chinese_to_int(self, chinese_num: str) -> Optional[int]:
        """将中文数字转换为整数"""
        if not chinese_num:
            return None

        # 如果是纯数字，直接返回
        if chinese_num.isdigit():
            return int(chinese_num)

        # 简单的中文数字转换
        result = 0
        temp = 0

        for char in chinese_num:
            if char in self.CHINESE_NUM_MAP:
                num = self.CHINESE_NUM_MAP[char]
                if num >= 10:
                    if temp == 0:
                        temp = 1
                    result += temp * num
                    temp = 0
                else:
                    temp = temp * 10 + num if temp else num
            else:
                return None

        result += temp
        return result if result > 0 else None

    def chunk_iter(
        self,
        text: str,
        config: ChunkConfig = None
    ) -> Generator[TextChunk, None, None]:
        """迭代式分块（用于流式处理）"""
        result = self.chunk(text, config)
        for chunk in result.chunks:
            yield chunk


# 便捷函数
def chunk_text(
    text: str,
    max_chunk_size: int = 2000,
    strategy: str = "paragraph"
) -> List[TextChunk]:
    """
    便捷函数：分块文本

    Args:
        text: 原始文本
        max_chunk_size: 最大块大小
        strategy: 分块策略 (paragraph/sliding/sentence/chapter)

    Returns:
        文本块列表
    """
    strategy_map = {
        "paragraph": ChunkStrategy.PARAGRAPH,
        "sliding": ChunkStrategy.SLIDING_WINDOW,
        "sentence": ChunkStrategy.SENTENCE,
        "chapter": ChunkStrategy.CHAPTER,
    }

    config = ChunkConfig(
        max_chunk_size=max_chunk_size,
        strategy=strategy_map.get(strategy, ChunkStrategy.PARAGRAPH)
    )

    chunker = TextChunker(config)
    result = chunker.chunk(text)
    return result.chunks
