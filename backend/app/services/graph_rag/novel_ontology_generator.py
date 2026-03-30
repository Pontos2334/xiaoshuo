"""
小说本体生成器

使用 LLM 从小说内容中生成实体类型和关系类型定义
"""

import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from anthropic import Anthropic

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class EntityType:
    """实体类型定义"""
    name: str
    description: str
    examples: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "examples": self.examples
        }


@dataclass
class RelationType:
    """关系类型定义"""
    name: str
    description: str
    source_types: List[str] = field(default_factory=list)
    target_types: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "source_types": self.source_types,
            "target_types": self.target_types
        }


@dataclass
class Ontology:
    """本体定义"""
    entity_types: List[EntityType]
    relation_types: List[RelationType]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_types": [et.to_dict() for et in self.entity_types],
            "relation_types": [rt.to_dict() for rt in self.relation_types]
        }


# 小说专用默认本体
DEFAULT_NOVEL_ONTOLOGY = Ontology(
    entity_types=[
        EntityType("Character", "人物：小说中的角色，包括主角、配角、龙套等",
                  ["张三", "李四", "王五"]),
        EntityType("Location", "地点：小说中的地理位置、场所、建筑等",
                  ["青云门", "天墉城", "玄机阁"]),
        EntityType("Organization", "组织/势力：门派、帮会、家族、朝廷等",
                  ["青云门", "天机阁", "皇室"]),
        EntityType("Item", "物品/法宝：武器、法器、丹药、秘籍等",
                  ["诛仙剑", "天书", "造化丹"]),
        EntityType("Event", "事件：小说中发生的重要事件、战斗、会议等",
                  ["青云大战", "武林大会", "诛仙之役"]),
        EntityType("Concept", "概念/功法：修炼体系、武学、法术、理念等",
                  ["太极", "五行", "道法"]),
        EntityType("Relationship", "关系：人物之间的社会关系，如师徒、朋友、敌人等",
                  ["师徒", "兄弟", "仇敌"]),
    ],
    relation_types=[
        RelationType("KNOWS", "认识：两个人物互相认识",
                    ["Character"], ["Character"]),
        RelationType("FAMILY_OF", "亲属：血缘或婚姻关系",
                    ["Character"], ["Character"]),
        RelationType("ENEMY_OF", "敌对：敌对关系，仇恨或冲突",
                    ["Character"], ["Character"]),
        RelationType("ALLIED_WITH", "结盟：合作关系或同盟",
                    ["Character", "Organization"], ["Character", "Organization"]),
        RelationType("MASTER_OF", "师徒：师傅与徒弟的关系",
                    ["Character"], ["Character"]),
        RelationType("LOCATED_AT", "位于：人物或物品所在的地点",
                    ["Character", "Item", "Organization"], ["Location"]),
        RelationType("OWNS", "拥有：人物拥有的物品或法宝",
                    ["Character"], ["Item"]),
        RelationType("MEMBER_OF", "成员：人物所属的组织或势力",
                    ["Character"], ["Organization"]),
        RelationType("PARTICIPATED_IN", "参与：人物参与的事件",
                    ["Character"], ["Event"]),
        RelationType("CAUSES", "导致：一个事件导致另一个事件",
                    ["Event"], ["Event"]),
        RelationType("RELATED_TO", "相关：通用关系类型",
                    ["Character", "Location", "Organization", "Item", "Event"],
                    ["Character", "Location", "Organization", "Item", "Event"]),
    ]
)


class NovelOntologyGenerator:
    """
    小说本体生成器

    使用 LLM 分析小说内容，生成适合该小说的本体定义
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
            logger.info(f"NovelOntologyGenerator 初始化完成: model={self.model}")
        else:
            self.client = None
            logger.warning("未配置 API Key，将使用默认本体")

    def generate(self, text_sample: str) -> Ontology:
        """
        从文本样本生成本体定义

        Args:
            text_sample: 小说文本样本（建议 5000-10000 字符）

        Returns:
            本体定义
        """
        if not self.client:
            logger.info("使用默认小说本体")
            return DEFAULT_NOVEL_ONTOLOGY

        # 限制文本长度
        if len(text_sample) > 8000:
            text_sample = text_sample[:8000]

        prompt = f"""分析以下小说文本，提取出其中的实体类型和关系类型。

【分析要求】
1. 识别文本中出现的实体类型（如人物、地点、组织、物品、事件等）
2. 识别实体之间的关系类型
3. 为每种类型提供简短的描述和示例

【小说文本】
{text_sample}

【输出格式】
请以 JSON 格式输出，包含以下字段：
- entity_types: 实体类型列表，每项包含 name, description, examples
- relation_types: 关系类型列表，每项包含 name, description, source_types, target_types

示例输出：
{{
  "entity_types": [
    {{"name": "Character", "description": "人物", "examples": ["张三", "李四"]}}
  ],
  "relation_types": [
    {{"name": "KNOWS", "description": "认识", "source_types": ["Character"], "target_types": ["Character"]}}
  ]
}}

请输出 JSON：
"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )

            content = response.content[0].text

            # 提取 JSON
            json_match = content[content.find('{'):content.rfind('}')+1]
            data = json.loads(json_match)

            # 构建本体
            entity_types = [
                EntityType(
                    name=et.get("name", "Entity"),
                    description=et.get("description", ""),
                    examples=et.get("examples", [])
                )
                for et in data.get("entity_types", [])
            ]

            relation_types = [
                RelationType(
                    name=rt.get("name", "RELATED_TO"),
                    description=rt.get("description", ""),
                    source_types=rt.get("source_types", []),
                    target_types=rt.get("target_types", [])
                )
                for rt in data.get("relation_types", [])
            ]

            logger.info(f"生成本体完成: {len(entity_types)} 个实体类型, {len(relation_types)} 个关系类型")
            return Ontology(entity_types=entity_types, relation_types=relation_types)

        except Exception as e:
            logger.error(f"生成本体失败: {e}，使用默认本体")
            return DEFAULT_NOVEL_ONTOLOGY

    def get_default_ontology(self) -> Ontology:
        """获取默认小说本体"""
        return DEFAULT_NOVEL_ONTOLOGY
