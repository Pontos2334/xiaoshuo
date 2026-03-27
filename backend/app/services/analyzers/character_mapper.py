"""
人物分析 Mapper

实现 Map-Reduce 模式中的人物分析 Map 阶段
"""

from typing import Dict, Any, List
import logging

from app.services.map_reduce_analyzer import Mapper, MapResult
from app.services.text_chunker import TextChunk
from app.agent.client import ClaudeAgentClient
from app.core.json_utils import JSONParser

logger = logging.getLogger(__name__)


class CharacterMapper(Mapper[List[Dict[str, Any]]]):
    """人物分析 Mapper"""

    def __init__(self):
        self.agent = ClaudeAgentClient()
        self.json_parser = JSONParser()

    async def map(self, chunk: TextChunk, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        分析单个文本块中的人物

        Args:
            chunk: 文本块
            context: 上下文（可能包含已有人物列表用于去重）

        Returns:
            人物列表
        """
        # 构建章节信息
        chapter_info = ""
        if chunk.chapter_num:
            chapter_info = f"（{chunk.chapter_title or f'第{chunk.chapter_num}章'}）"
        else:
            chapter_info = f"（片段 {chunk.index + 1}）"

        prompt = f"""请分析以下小说片段，提取其中出现的所有人物信息。

小说片段{chapter_info}：
{chunk.content}

请以JSON格式返回人物列表，每个人物包含以下字段：
- name: 姓名
- aliases: 别名/绰号列表
- basic_info: 基本信息（年龄、性别、身份等）
- personality: 性格特点列表
- abilities: 能力/技能列表
- story_summary: 这个片段中的故事简介
- first_appear: 首次出现的章节（如果有）

注意：
1. 只提取这个片段中明确出现或有明确描述的人物
2. 不要遗漏任何有名字的角色
3. 即使是一笔带过的角色也要记录
4. 性格和能力要基于文本内容，不要臆测

只返回JSON数组，不要其他内容。"""

        response = await self.agent.generate(prompt)
        characters = self.json_parser.safe_parse_json(response, default=[])

        if not characters:
            logger.warning(f"块 {chunk.index} 未识别到人物")
            return []

        # 添加元数据
        for char in characters:
            char['_chunk_index'] = chunk.index
            if chunk.chapter_num:
                char['_chapter_num'] = chunk.chapter_num

        logger.debug(f"块 {chunk.index} 识别到 {len(characters)} 个人物")
        return characters
