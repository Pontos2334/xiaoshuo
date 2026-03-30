"""
人物档案生成器

从小说内容和人物信息生成详细的人物档案，用于对话系统
"""

import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from anthropic import Anthropic

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class CharacterProfile:
    """人物档案"""
    character_id: str
    name: str
    bio: str = ""                      # 简短简介
    persona: str = ""                   # 详细人设（用于 LLM 系统提示）
    personality: List[str] = field(default_factory=list)  # 性格特点
    speaking_style: str = ""            # 说话风格
    background: str = ""                # 背景故事
    relationships: Dict[str, str] = field(default_factory=dict)  # 与他人的关系
    key_events: List[str] = field(default_factory=list)  # 关键事件

    def to_dict(self) -> Dict[str, Any]:
        return {
            "character_id": self.character_id,
            "name": self.name,
            "bio": self.bio,
            "persona": self.persona,
            "personality": self.personality,
            "speaking_style": self.speaking_style,
            "background": self.background,
            "relationships": self.relationships,
            "key_events": self.key_events
        }

    def get_system_prompt(self) -> str:
        """获取用于对话的系统提示"""
        return f"""你现在扮演小说中的人物【{self.name}】。

【人物简介】
{self.bio}

【性格特点】
{', '.join(self.personality) if self.personality else '（未指定）'}

【说话风格】
{self.speaking_style if self.speaking_style else '保持人物特点，说话自然'}

【背景故事】
{self.background if self.background else '（未指定）'}

【与其他人物的关系】
{self._format_relationships()}

【关键经历】
{self._format_key_events()}

【角色扮演要求】
1. 严格保持{self.name}的性格特点和说话风格
2. 回答要符合人物背景和经历
3. 提到相关人物时要符合设定的人物关系
4. 可以适当展开想象，但不能与基本设定矛盾
5. 用第一人称说话，仿佛你就是{self.name}本人
"""

    def _format_relationships(self) -> str:
        """格式化人物关系"""
        if not self.relationships:
            return "（未指定）"
        return "\n".join([f"- {name}: {rel}" for name, rel in self.relationships.items()])

    def _format_key_events(self) -> str:
        """格式化关键事件"""
        if not self.key_events:
            return "（未指定）"
        return "\n".join([f"- {event}" for event in self.key_events])


class CharacterProfileGenerator:
    """
    人物档案生成器

    使用 LLM 从人物信息和小说内容生成详细的人物档案
    """

    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.base_url = base_url or settings.ANTHROPIC_BASE_URL
        self.model = model or settings.CLAUDE_MODEL

        if self.api_key:
            self.client = Anthropic(
                api_key=self.api_key,
                base_url=self.base_url
            )
            logger.info(f"CharacterProfileGenerator 初始化完成: model={self.model}")
        else:
            self.client = None
            logger.warning("未配置 API Key，档案生成将返回基本信息")

    def generate(
        self,
        character_id: str,
        character_data: Dict[str, Any],
        novel_context: str = "",
        relations: List[Dict[str, Any]] = None
    ) -> CharacterProfile:
        """
        生成人物档案

        Args:
            character_id: 人物ID
            character_data: 人物数据（来自数据库）
            novel_context: 小说上下文（相关片段）
            relations: 人物关系列表

        Returns:
            人物档案
        """
        name = character_data.get("name", "未知人物")

        if not self.client:
            # 无 API 时返回基本档案
            return CharacterProfile(
                character_id=character_id,
                name=name,
                bio=character_data.get("story_summary", ""),
                personality=character_data.get("personality", []),
                background=character_data.get("basic_info", {}).get("background", "")
            )

        # 构建提示词
        prompt = self._build_prompt(name, character_data, novel_context, relations)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )

            content = response.content[0].text

            # 解析结果
            return self._parse_response(character_id, name, content, character_data)

        except Exception as e:
            logger.error(f"生成人物档案失败: {e}")
            # 返回基本档案
            return CharacterProfile(
                character_id=character_id,
                name=name,
                bio=character_data.get("story_summary", ""),
                personality=character_data.get("personality", [])
            )

    def _build_prompt(
        self,
        name: str,
        character_data: Dict[str, Any],
        novel_context: str,
        relations: List[Dict[str, Any]]
    ) -> str:
        """构建生成提示词"""
        # 提取已有信息
        basic_info = character_data.get("basic_info", {})
        personality = character_data.get("personality", [])
        story_summary = character_data.get("story_summary", "")
        abilities = character_data.get("abilities", [])

        # 格式化关系
        rel_text = ""
        if relations:
            rel_lines = []
            for rel in relations:
                target = rel.get("target_name", rel.get("target", ""))
                rel_type = rel.get("relation_type", "相关")
                desc = rel.get("description", "")
                if desc:
                    rel_lines.append(f"- {target}: {rel_type} ({desc})")
                else:
                    rel_lines.append(f"- {target}: {rel_type}")
            rel_text = "\n".join(rel_lines)

        # 限制小说上下文长度
        if len(novel_context) > 5000:
            novel_context = novel_context[:5000] + "..."

        prompt = f"""请根据以下信息，为小说人物【{name}】生成详细的人物档案。

【已有基本信息】
- 姓名: {name}
- 身份: {basic_info.get("identity", "未指定")}
- 简介: {story_summary}
- 性格: {', '.join(personality) if personality else "未指定"}
- 能力: {', '.join(abilities) if abilities else "未指定"}

【人物关系】
{rel_text if rel_text else "（暂无关系信息）"}

【小说相关片段】
{novel_context if novel_context else "（暂无相关片段）"}

【输出要求】
请以 JSON 格式输出以下字段：
1. bio: 100-200字的人物简介
2. persona: 详细的系统提示词，用于角色扮演（300-500字）
3. personality: 3-5个性格特点的数组
4. speaking_style: 说话风格描述（如：幽默风趣、严肃认真、古风文雅等）
5. background: 背景故事概述（100-200字）
6. key_events: 3-5个关键事件的数组

示例输出：
{{
  "bio": "张三是青云门的天才弟子...",
  "persona": "你是张三，青云门的天才弟子...",
  "personality": ["聪明", "正义", "执着"],
  "speaking_style": "古风文雅，带有修仙者的从容",
  "background": "自幼被青云门收养...",
  "key_events": ["拜入青云门", "获得诛仙剑", "参加青云大战"]
}}

请输出 JSON：
"""
        return prompt

    def _parse_response(
        self,
        character_id: str,
        name: str,
        content: str,
        character_data: Dict[str, Any]
    ) -> CharacterProfile:
        """解析 LLM 响应"""
        try:
            # 提取 JSON
            json_match = content[content.find('{'):content.rfind('}')+1]
            data = json.loads(json_match)

            # 构建关系字典
            relationships = {}
            for rel in character_data.get("relations", []):
                target = rel.get("target_name", rel.get("target", ""))
                rel_type = rel.get("relation_type", "")
                if target and rel_type:
                    relationships[target] = rel_type

            return CharacterProfile(
                character_id=character_id,
                name=name,
                bio=data.get("bio", ""),
                persona=data.get("persona", ""),
                personality=data.get("personality", []),
                speaking_style=data.get("speaking_style", ""),
                background=data.get("background", ""),
                relationships=relationships,
                key_events=data.get("key_events", [])
            )

        except Exception as e:
            logger.warning(f"解析人物档案失败: {e}")
            return CharacterProfile(
                character_id=character_id,
                name=name,
                bio=character_data.get("story_summary", ""),
                personality=character_data.get("personality", [])
            )

    def enhance_profile_with_context(
        self,
        profile: CharacterProfile,
        additional_context: str
    ) -> CharacterProfile:
        """
        使用额外上下文增强人物档案

        Args:
            profile: 现有档案
            additional_context: 额外的小说上下文

        Returns:
            增强后的档案
        """
        if not self.client:
            return profile

        prompt = f"""基于以下人物档案和新的小说片段，补充和丰富人物信息。

【现有档案】
{json.dumps(profile.to_dict(), ensure_ascii=False, indent=2)}

【新的小说片段】
{additional_context[:3000]}

【任务】
请根据新片段，补充或修正人物档案中的信息。以 JSON 格式输出更新后的完整档案（包含所有字段）。
"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )

            content = response.content[0].text
            json_match = content[content.find('{'):content.rfind('}')+1]
            data = json.loads(json_match)

            return CharacterProfile(
                character_id=profile.character_id,
                name=profile.name,
                bio=data.get("bio", profile.bio),
                persona=data.get("persona", profile.persona),
                personality=data.get("personality", profile.personality),
                speaking_style=data.get("speaking_style", profile.speaking_style),
                background=data.get("background", profile.background),
                relationships={**profile.relationships, **data.get("relationships", {})},
                key_events=data.get("key_events", profile.key_events)
            )

        except Exception as e:
            logger.warning(f"增强人物档案失败: {e}")
            return profile
