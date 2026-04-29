"""角色成长弧线分析服务 - 追踪角色在各章节中的状态变化"""

import logging
from app.agent.client import ClaudeAgentClient
from app.core.json_utils import JSONParser

logger = logging.getLogger(__name__)


class CharacterArcAnalyzer:
    """角色成长弧线分析器"""

    def __init__(self):
        self.client = ClaudeAgentClient()
        self.json_parser = JSONParser()

    async def extract_arc_points(self, character: dict, chapters_content: str) -> list:
        """从小说文本中提取角色在各章节的状态变化

        Args:
            character: 角色信息字典，包含 name, aliases, personality, abilities 等
            chapters_content: 小说章节文本（截断到15000字符）

        Returns:
            角色弧线点列表，每个包含 chapter_number, psychological_state, emotional_state 等
        """
        char_name = character.get("name", "未知角色")
        aliases = character.get("aliases", [])
        personality = character.get("personality", [])
        abilities = character.get("abilities", [])
        story_summary = character.get("story_summary", "")

        aliases_str = "、".join(aliases) if isinstance(aliases, list) else str(aliases)
        personality_str = "、".join(personality) if isinstance(personality, list) else str(personality)
        abilities_str = "、".join(abilities) if isinstance(abilities, list) else str(abilities)

        truncated = chapters_content[:15000]

        prompt = f"""你是一位专业的小说分析师，擅长追踪角色在故事中的成长与变化。

【角色信息】
- 姓名：{char_name}
- 别名：{aliases_str or '无'}
- 性格特点：{personality_str or '未知'}
- 能力技能：{abilities_str or '未知'}
- 故事简介：{story_summary or '未知'}

【小说内容】
{truncated}

【任务】
请仔细分析以上小说内容，追踪角色「{char_name}」在各章节中的状态变化。

对每个出现该角色的章节，提取以下信息：
1. chapter_number: 章节编号（整数）
2. psychological_state: 心理状态（如：迷茫、坚定、动摇、自信、恐惧、释然等）
3. emotional_state: 情感状态（如：愤怒、悲伤、平静、喜悦、焦虑、绝望等）
4. ability_description: 该章节中展现的能力描述（如无变化可简述当前水平）
5. ability_level: 能力等级评估（1-10，整数，null表示无法判断）
6. key_events: 该章节中与该角色相关的关键事件列表

请以JSON数组格式返回，只返回JSON，不要其他内容。
示例格式：
[
  {{
    "chapter_number": 1,
    "psychological_state": "迷茫",
    "emotional_state": "焦虑",
    "ability_description": "初入江湖，武功平平",
    "ability_level": 2,
    "key_events": ["被师父收留", "开始修炼基本功"]
  }}
]"""

        try:
            response = await self.client.generate(prompt)
            result = self.json_parser.safe_parse_json(response, default=[])
            if isinstance(result, list):
                return result
            return []
        except Exception as e:
            logger.warning(f"提取角色弧线点失败 ({char_name}): {e}")
            return []

    async def detect_inconsistencies(self, arc_points: list, character_name: str) -> list:
        """检测角色弧线中的不一致性（突然的性格变化无铺垫等）

        Args:
            arc_points: 按chapter_number排序的弧线点列表
            character_name: 角色名称

        Returns:
            不一致性问题列表
        """
        if len(arc_points) < 2:
            return []

        # 构建弧线摘要
        arc_summary = "\n".join([
            f"第{p.get('chapter_number', '?')}章: 心理={p.get('psychological_state', '未知')}, "
            f"情感={p.get('emotional_state', '未知')}, "
            f"能力={p.get('ability_description', '未知')}, "
            f"等级={p.get('ability_level', '未知')}"
            for p in arc_points
        ])

        prompt = f"""你是一位专业的小说编辑，擅长发现角色塑造中的问题。

【角色名称】{character_name}

【角色成长弧线】
{arc_summary}

【任务】
请检查这个角色的成长弧线是否存在以下问题：
1. 心理状态突然大幅变化，但中间没有足够的事件铺垫
2. 能力等级突兀跳跃（如突然从2级跳到8级，没有修炼或奇遇描写）
3. 情感状态前后矛盾（如同一个人对同一事件反应完全不同，且无合理解释）
4. 角色弧线缺乏成长感（长期停滞不变）

请以JSON数组格式返回发现的问题：
[
  {{
    "description": "问题描述",
    "from_chapter": 起始章节号,
    "to_chapter": 结束章节号,
    "severity": "error/warning/info"
  }}
]

如果没有发现问题，返回空数组 []。
只返回JSON，不要其他内容。"""

        try:
            response = await self.client.generate(prompt)
            result = self.json_parser.safe_parse_json(response, default=[])
            if isinstance(result, list):
                return result
            return []
        except Exception as e:
            logger.warning(f"检测角色弧线不一致性失败 ({character_name}): {e}")
            return []

    def generate_growth_curve(self, arc_points: list) -> dict:
        """生成角色成长曲线数据（纯计算，不调用AI）

        Args:
            arc_points: 弧线点列表

        Returns:
            {chapter_number: ability_level} 的映射字典
        """
        curve = {}
        for point in arc_points:
            chapter = point.get("chapter_number")
            level = point.get("ability_level")
            if chapter is not None and level is not None:
                curve[chapter] = level
        return curve
