import re
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.agent.client import ClaudeAgentClient
from app.core.json_utils import JSONParser
from app.services.chapter_splitter import chapter_splitter

logger = logging.getLogger(__name__)

# 常量定义
MAX_CONTENT_LENGTH = 15000  # 增加到15000字符
MAX_RELATION_CONTENT_LENGTH = 10000
MAX_CHAPTER_CONTENT = 8000  # 单章最大内容


class CharacterAnalyzer:
    """人物分析服务"""

    def __init__(self):
        self.agent = ClaudeAgentClient()
        self.json_parser = JSONParser()

    async def analyze(self, content: str) -> List[Dict[str, Any]]:
        """全量分析小说内容，提取人物信息"""
        truncated_content = content[:MAX_CONTENT_LENGTH]
        prompt = f"""请分析以下小说内容，提取所有重要人物的信息。

小说内容：
{truncated_content}

请以JSON格式返回人物列表，每个人物包含以下字段：
- name: 姓名
- aliases: 别名/绰号列表
- basic_info: 基本信息（年龄、性别、身份等）
- personality: 性格特点列表
- abilities: 能力/技能列表
- story_summary: 角色故事简介
- first_appear: 首次出现的章节（如果有）

只返回JSON数组，不要其他内容。"""

        response = await self.agent.generate(prompt)

        characters = self.json_parser.safe_parse_json(response, default=[])
        if not characters:
            logger.warning(f"人物分析返回空结果，原始响应: {response[:200]}...")
        return characters

    async def analyze_incremental(
        self,
        content: str,
        existing_characters: List[Dict[str, Any]],
        start_chapter: int,
        ai_version: int = 1
    ) -> List[Dict[str, Any]]:
        """
        嶞量分析：只分析新章节，保留用户修改的数据

        Args:
            content: 小说全文内容
            existing_characters: 现有人物数据
            start_chapter: 起始章节号
            ai_version: 当前AI分析版本号

        Returns:
            合并后的人物列表
        """
        # 获取新章节内容
        new_chapters = chapter_splitter.get_chapters_from_position(content, start_chapter)
        if not new_chapters:
            logger.info(f"没有发现新章节（从第{start_chapter}章开始）")
            return existing_characters

        # 合并新章节内容
        new_content_parts = []
        for chapter in new_chapters:
            if len(chapter) > 2:
                new_content_parts.append(chapter[2])  # 章节内容

        new_content = '\n\n'.join(new_content_parts)
        if not new_content.strip():
            logger.info("新章节内容为空")
            return existing_characters

        # 分析新内容
        truncated_new = new_content[:MAX_CONTENT_LENGTH]
        prompt = f"""请分析以下小说新内容，提取其中出现的人物信息。

小说内容：
{truncated_new}

注意：
1. 只提取这个片段中新出现或有人物新信息的人物
2. 如果人物在已有信息中有更新，请标注更新内容

请以JSON格式返回人物列表，每个人物包含以下字段：
- name: 姓名（必须）
- aliases: 别名/绰号列表
- basic_info: 基本信息
- personality: 性格特点列表
- abilities: 能力/技能列表
- story_summary: 这个片段中的故事简介
- first_appear: 首次出现的章节
- is_new: 是否是新人物（true/false）
- updates: 对现有人物的更新信息（如果有）

只返回JSON数组，不要其他内容。"""

        response = await self.agent.generate(prompt)
        new_characters = self.json_parser.safe_parse_json(response, default=[])

        # 合并数据
        merged = self._merge_characters(existing_characters, new_characters, ai_version)
        return merged

    def _merge_characters(
        self,
        existing: List[Dict[str, Any]],
        new_data: List[Dict[str, Any]],
        ai_version: int
    ) -> List[Dict[str, Any]]:
        """
        合并现有人物和新分析的人物数据

        保留 source='user' 或 'ai_modified' 的数据
        """
        # 创建名字到人物的映射
        existing_map = {}
        for char in existing:
            name = char.get('name', '')
            if name:
                # 标准化名字用于匹配
                normalized_name = re.sub(r'\s+', '', name.strip())
                existing_map[normalized_name] = char

        # 处理新数据
        result = []
        processed_names = set()

        for new_char in new_data:
            name = new_char.get('name', '')
            if not name:
                continue

            normalized_name = re.sub(r'\s+', '', name.strip())

            if normalized_name in existing_map:
                # 已有人物 - 检查是否需要更新
                existing_char = existing_map[normalized_name]
                source = existing_char.get('source', 'ai')

                if source in ('user', 'ai_modified'):
                    # 用户修改过 - 保留原数据，但可以添加新信息
                    merged_char = {**existing_char}
                    # 添加新的别名
                    if new_char.get('aliases'):
                        existing_aliases = merged_char.get('aliases', [])
                        for alias in new_char.get('aliases', []):
                            if alias not in existing_aliases:
                                existing_aliases.append(alias)
                        merged_char['aliases'] = existing_aliases
                    # 标记为已修改
                    merged_char['source'] = 'ai_modified'
                    result.append(merged_char)
                else:
                    # AI生成的数据 - 可以更新
                    merged_char = {**existing_char, **new_char}
                    merged_char['source'] = 'ai'
                    merged_char['ai_version'] = ai_version
                    result.append(merged_char)
            else:
                # 新人物
                new_char['source'] = 'ai'
                new_char['ai_version'] = ai_version
                result.append(new_char)

            processed_names.add(normalized_name)

        # 添加未处理的人物（没有新信息的）
        for char in existing:
            name = char.get('name', '')
            if name:
                normalized_name = re.sub(r'\s+', '', name.strip())
                if normalized_name not in processed_names:
                    result.append(char)

        return result

    async def analyze_relations(self, content: str, characters: List[Any]) -> List[Dict[str, Any]]:
        """分析人物关系"""
        char_info = "\n".join([
            f"- {c.name}（ID: {c.id}）：{getattr(c, 'story_summary', '暂无简介')}"
            for c in characters
        ])

        truncated_content = content[:MAX_RELATION_CONTENT_LENGTH]
        prompt = f"""请分析以下小说内容和人物列表，提取人物之间的关系。

小说内容：
{truncated_content}

人物列表：
{char_info}

请以JSON格式返回关系列表，每个关系包含以下字段：
- source_id: 源人物ID
- target_id: 目标人物ID
- relation_type: 关系类型
- description: 关系描述
- strength: 关系强度（1-10）

只返回JSON数组，不要其他内容。"""

        response = await self.agent.generate(prompt)

        relations = self.json_parser.safe_parse_json(response, default=[])
        if not relations:
            logger.warning(f"关系分析返回空结果，原始响应: {response[:200]}...")
        return relations
