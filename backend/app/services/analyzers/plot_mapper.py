"""
情节分析 Mapper

实现 Map-Reduce 模式中的情节分析 Map 阶段
"""

from typing import Dict, Any, List
import logging

from app.services.map_reduce_analyzer import Mapper, MapResult
from app.services.text_chunker import TextChunk
from app.agent.client import ClaudeAgentClient
from app.core.json_utils import JSONParser

logger = logging.getLogger(__name__)


class PlotMapper(Mapper[List[Dict[str, Any]]]):
    """情节分析 Mapper"""

    def __init__(self):
        self.agent = ClaudeAgentClient()
        self.json_parser = JSONParser()

    async def map(self, chunk: TextChunk, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        分析单个文本块中的情节节点

        Args:
            chunk: 文本块
            context: 上下文（可能包含大纲、已有情节等）

        Returns:
            情节节点列表
        """
        outline = context.get('outline', '暂无大纲')

        # 构建章节信息
        chapter_info = ""
        if chunk.chapter_num:
            chapter_info = f"（{chunk.chapter_title or f'第{chunk.chapter_num}章'}）"
        else:
            chapter_info = f"（片段 {chunk.index + 1}）"

        prompt = f"""请分析以下小说片段，提取其中的主要情节节点。

小说大纲（参考）：
{outline[:2000] if outline else '暂无大纲'}

小说片段{chapter_info}：
{chunk.content}

请提取这个片段中的情节节点，以JSON格式返回，每个节点包含：
- title: 情节标题（简洁概括，5-10字）
- chapter: 所属章节（数字，如 1、2、3）
- summary: 情节概述（100-150字）
- characters: 涉及的主要人物名称列表
- emotion: 主要情绪（如：紧张、温馨、悲伤、热血等）
- importance: 重要程度（1-10，10最重要）
- content_ref: 原文关键引用（20字以内，用于定位）

注意：
1. 只提取这个片段中的情节，不要推测后续发展
2. 每个情节点应该是一个独立的事件
3. 按时间顺序排列
4. 标题要简洁有力，能概括事件核心
5. 重要性评分要客观，关键转折点给高分

只返回JSON数组，不要其他内容。"""

        response = await self.agent.generate(prompt)
        plots = self.json_parser.safe_parse_json(response, default=[])

        if not plots:
            logger.warning(f"块 {chunk.index} 未识别到情节")
            return []

        # 添加元数据
        for plot in plots:
            plot['_chunk_index'] = chunk.index
            if chunk.chapter_num and not plot.get('chapter'):
                plot['chapter'] = chunk.chapter_num

        logger.debug(f"块 {chunk.index} 识别到 {len(plots)} 个情节节点")
        return plots
