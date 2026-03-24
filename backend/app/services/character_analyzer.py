import logging
from typing import List, Dict, Any
from app.agent.client import ClaudeAgentClient
from app.core.json_utils import JSONParser

logger = logging.getLogger(__name__)

# 常量定义（替代魔法数字）
MAX_CONTENT_LENGTH = 10000
MAX_RELATION_CONTENT_LENGTH = 8000


class CharacterAnalyzer:
    """人物分析服务"""

    def __init__(self):
        self.agent = ClaudeAgentClient()
        self.json_parser = JSONParser()

    async def analyze(self, content: str) -> List[Dict[str, Any]]:
        """分析小说内容，提取人物信息"""
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
