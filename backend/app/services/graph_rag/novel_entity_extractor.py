"""
小说实体抽取器

基于 GraphRAG 方案，使用 LLM 从小说文本中抽取实体和关系
支持多轮抽取 (Gleaning) 最大化实体数量
"""

import os
import re
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field

from anthropic import Anthropic

logger = logging.getLogger(__name__)


# 分隔符定义
TUPLE_DELIMITER = "<|>"
RECORD_DELIMITER = "##"
COMPLETION_DELIMITER = "<|COMPLETE|>"


@dataclass
class ExtractedEntity:
    """抽取的实体"""
    name: str
    entity_type: str
    description: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.entity_type,
            "description": self.description,
            "attributes": self.attributes
        }


@dataclass
class ExtractedRelation:
    """抽取的关系"""
    source: str
    target: str
    relation_type: str
    description: str = ""
    strength: int = 5
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "type": self.relation_type,
            "description": self.description,
            "strength": self.strength,
            "attributes": self.attributes
        }


@dataclass
class ExtractionResult:
    """抽取结果"""
    entities: List[ExtractedEntity] = field(default_factory=list)
    relations: List[ExtractedRelation] = field(default_factory=list)
    summary: str = ""
    topics: List[str] = field(default_factory=list)


# GraphRAG 风格的实体抽取提示词
GRAPH_EXTRACTION_PROMPT = """---Goal---
给定一段小说文本和一系列实体类型，请从文本中识别出所有这些类型的实体，以及这些实体之间的关系。

---Steps---
1. 识别所有实体。对于每个识别出的实体，提取以下信息：
- entity_name: 实体名称，使用原文中的名称
- entity_type: 以下类型之一: [{entity_types}]
- entity_description: 基于文本提供实体的描述

格式：("entity"{tuple_delimiter}<entity_name>{tuple_delimiter}<entity_type>{tuple_delimiter}<entity_description>)

2. 从步骤1识别的实体中，识别所有相互之间有明显关系的(源实体, 目标实体)对。
对于每对相关实体，提取以下信息：
- source_entity: 源实体名称
- target_entity: 目标实体名称
- relationship_description: 解释为什么认为两个实体相关
- relationship_keywords: 概括关系类型的关键词（如：师徒、朋友、敌对、所属等）
- relationship_strength: 关系强度评分 (1-10)

格式：("relationship"{tuple_delimiter}<source_entity>{tuple_delimiter}<target_entity>{tuple_delimiter}<relationship_description>{tuple_delimiter}<relationship_keywords>{tuple_delimiter}<relationship_strength>)

3. 使用 {record_delimiter} 作为列表分隔符
4. 完成后，输出 {completion_delimiter}

---Examples---
{examples}

---Real Data---
Entity_types: [{entity_types}]
Text: {input_text}
Output:"""

# Few-Shot 示例
ENTITY_EXTRACTION_EXAMPLES = """
Example 1:

Entity_types: [Character, Location, Organization, Item, Event]
Text:
```
张三是青云门的弟子，从小在天墉城长大。他的师父是玄机长老，与师妹李四感情很好。
张三拥有一把诛仙剑，这是青云门的镇派之宝。他参与了青云大战，与魔教教主王五决一死战。
```

Output:
("entity"<|>"张三"<|>"Character"<|>"张三是青云门的弟子，从小在天墉城长大，拥有诛仙剑")##
("entity"<|>"青云门"<|>"Organization"<|>"青云门是修仙门派，镇派之宝是诛仙剑")##
("entity"<|>"天墉城"<|>"Location"<|>"天墉城是张三长大的地方")##
("entity"<|>"玄机长老"<|>"Character"<|>"玄机长老是张三的师父")##
("entity"<|>"李四"<|>"Character"<|>"李四是张三的师妹，两人感情很好")##
("entity"<|>"诛仙剑"<|>"Item"<|>"诛仙剑是青云门的镇派之宝，由张三拥有")##
("entity"<|>"青云大战"<|>"Event"<|>"青云大战是张三与王五决战的重大事件")##
("entity"<|>"王五"<|>"Character"<|>"王五是魔教教主，与张三是敌对关系")##
("relationship"<|>"张三"<|>"青云门"<|>"张三是青云门的弟子"<|>"弟子, 所属"<|>9)##
("relationship"<|>"张三"<|>"天墉城"<|>"张三在天墉城长大"<|>"位于, 成长"<|>6)##
("relationship"<|>"张三"<|>"玄机长老"<|>"玄机长老是张三的师父"<|>"师徒, 师父"<|>8)##
("relationship"<|>"张三"<|>"李四"<|>"张三和李四是师兄妹，感情很好"<|>"师兄妹, 感情好"<|>7)##
("relationship"<|>"张三"<|>"诛仙剑"<|>"张三拥有诛仙剑"<|>"拥有, 佩剑"<|>8)##
("relationship"<|>"张三"<|>"王五"<|>"张三与王五是敌对关系"<|>"敌对, 决战"<|>9)##
("relationship"<|>"青云门"<|>"诛仙剑"<|>"诛仙剑是青云门的镇派之宝"<|>"镇派, 所属"<|>8)<|COMPLETE|>
"""

# 继续抽取提示词
CONTINUE_PROMPT = """
上次抽取遗漏了一些实体。请仅从文本中找出之前遗漏的实体和关系。

使用相同格式在下方添加新的实体和关系：
"""


class NovelEntityExtractor:
    """
    小说实体抽取器

    基于 GraphRAG 的多轮抽取方法
    """

    # 默认实体类型
    DEFAULT_ENTITY_TYPES = [
        "Character",     # 人物
        "Location",      # 地点
        "Organization",  # 组织/势力
        "Item",          # 物品/法宝
        "Event",         # 事件
        "Concept",       # 概念/功法
    ]

    def __init__(
        self,
        api_key: str = None,
        base_url: str = None,
        model: str = None,
        max_gleanings: int = 1,
        entity_types: List[str] = None
    ):
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        self.base_url = base_url or os.getenv('ANTHROPIC_BASE_URL')
        self.model = model or os.getenv('CLAUDE_MODEL', 'glm-5')
        self.max_gleanings = max_gleanings
        self.entity_types = entity_types or self.DEFAULT_ENTITY_TYPES

        if self.api_key:
            self.client = Anthropic(
                api_key=self.api_key,
                base_url=self.base_url
            )
            logger.info(f"NovelEntityExtractor 初始化完成: model={self.model}, max_gleanings={max_gleanings}")
        else:
            self.client = None
            logger.warning("未配置 API Key，抽取器将返回空结果")

    def extract(
        self,
        text: str,
        entity_types: List[str] = None,
        ontology: Dict[str, Any] = None
    ) -> ExtractionResult:
        """
        从文本中抽取实体和关系

        Args:
            text: 待抽取的文本
            entity_types: 实体类型列表（可选）
            ontology: 本体定义（可选）

        Returns:
            抽取结果
        """
        if not self.client:
            logger.warning("API 客户端未初始化，返回空结果")
            return ExtractionResult()

        # 确定实体类型
        types = entity_types or self.entity_types
        if ontology:
            types = [et.get("name") for et in ontology.get("entity_types", [])] or types

        # 根据文本长度选择策略
        if len(text) < 2000:
            return self._extract_short(text, types)
        else:
            return self._extract_long(text, types)

    def _extract_short(
        self,
        text: str,
        entity_types: List[str]
    ) -> ExtractionResult:
        """
        短文本抽取：多轮抽取
        """
        results = ""
        types_str = ",".join(entity_types)

        # 构建初始提示词
        prompt = GRAPH_EXTRACTION_PROMPT.format(
            tuple_delimiter=TUPLE_DELIMITER,
            record_delimiter=RECORD_DELIMITER,
            completion_delimiter=COMPLETION_DELIMITER,
            entity_types=types_str,
            examples=ENTITY_EXTRACTION_EXAMPLES,
            input_text=text
        )

        # 第一次抽取
        response = self._call_llm(prompt)
        results += response

        # 多轮抽取 (Gleaning)
        for i in range(self.max_gleanings):
            continue_prompt = CONTINUE_PROMPT
            response = self._call_llm(continue_prompt)
            if not response or COMPLETION_DELIMITER in response:
                break
            results += RECORD_DELIMITER + response

        # 解析结果
        entities, relations = self._parse_results(results)

        logger.info(f"短文本抽取完成: {len(entities)} 个实体, {len(relations)} 个关系")

        return ExtractionResult(entities=entities, relations=relations)

    def _extract_long(
        self,
        text: str,
        entity_types: List[str]
    ) -> ExtractionResult:
        """
        长文本抽取：分段处理 + 实体去重
        """
        # 智能分段
        chunks = self._split_text(text)

        all_entities = []
        all_relations = []
        entity_keys = set()  # 去重用: name|type

        for i, chunk in enumerate(chunks):
            if len(chunk.strip()) < 100:
                continue

            result = self._extract_short(chunk, entity_types)

            # 去重添加实体
            for entity in result.entities:
                key = f"{entity.name}|{entity.entity_type}"
                if key not in entity_keys:
                    all_entities.append(entity)
                    entity_keys.add(key)

            all_relations.extend(result.relations)

            if (i + 1) % 3 == 0:
                logger.debug(f"已处理 {i+1}/{len(chunks)} 个文本块")

        # 关系去重
        unique_relations = self._deduplicate_relations(all_relations)

        logger.info(f"长文本抽取完成: {len(chunks)} 个文本块, {len(all_entities)} 个实体, {len(unique_relations)} 个关系")

        return ExtractionResult(entities=all_entities, relations=unique_relations)

    def _call_llm(self, prompt: str, max_tokens: int = 3000) -> str:
        """调用 LLM"""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            return ""

    def _parse_results(
        self,
        results: str
    ) -> Tuple[List[ExtractedEntity], List[ExtractedRelation]]:
        """
        解析 GraphRAG 格式的抽取结果
        """
        entities = []
        relations = []

        # 按记录分隔符分割
        records = re.split(
            f'({re.escape(RECORD_DELIMITER)}|{re.escape(COMPLETION_DELIMITER)})',
            results
        )

        for record in records:
            record = record.strip()
            if not record or record in [RECORD_DELIMITER, COMPLETION_DELIMITER]:
                continue

            # 提取括号内的内容
            match = re.search(r'\((.*)\)', record)
            if not match:
                continue

            content = match.group(1)

            # 按元组分隔符分割
            parts = content.split(TUPLE_DELIMITER)

            if len(parts) < 3:
                continue

            # 去除引号
            record_type = parts[0].strip().strip('"').strip("'")

            if record_type == "entity" and len(parts) >= 4:
                # ("entity"<|><name><|><type><|><description>)
                entity_name = parts[1].strip().strip('"').strip("'")
                entity_type = parts[2].strip().strip('"').strip("'")
                entity_desc = parts[3].strip().strip('"').strip("'")

                if not entity_name:
                    continue

                entities.append(ExtractedEntity(
                    name=entity_name,
                    entity_type=entity_type,
                    description=entity_desc
                ))

            elif record_type == "relationship":
                # ("relationship"<|><source><|><target><|><desc><|><keywords><|><strength>)
                try:
                    if len(parts) >= 6:
                        keywords = parts[4].strip().strip('"').strip("'")
                        strength_str = parts[5].strip().strip('"').strip("'")
                    elif len(parts) >= 5:
                        keywords = parts[4].strip().strip('"').strip("'")
                        strength_str = "5"
                    else:
                        keywords = ""
                        strength_str = "5"

                    strength = 5
                    if strength_str.isdigit():
                        strength = int(strength_str)

                    # 标准化关系类型
                    relation_type = self._normalize_relation_type(keywords)

                    relations.append(ExtractedRelation(
                        source=parts[1].strip().strip('"').strip("'"),
                        target=parts[2].strip().strip('"').strip("'"),
                        relation_type=relation_type,
                        description=parts[3].strip().strip('"').strip("'"),
                        strength=max(1, min(10, strength)),
                        attributes={"keywords": keywords} if keywords else {}
                    ))
                except Exception as e:
                    logger.debug(f"关系解析失败: {e}")

        return entities, relations

    def _normalize_relation_type(self, keywords: str) -> str:
        """标准化关系类型"""
        if not keywords:
            return "RELATED_TO"

        # 关系类型映射
        relation_map = {
            "师徒": "MASTER_OF",
            "师傅": "MASTER_OF",
            "徒弟": "MASTER_OF",
            "师父": "MASTER_OF",
            "朋友": "FRIEND_OF",
            "敌对": "ENEMY_OF",
            "敌人": "ENEMY_OF",
            "仇人": "ENEMY_OF",
            "亲属": "FAMILY_OF",
            "兄弟": "FAMILY_OF",
            "姐妹": "FAMILY_OF",
            "父子": "FAMILY_OF",
            "母女": "FAMILY_OF",
            "结盟": "ALLIED_WITH",
            "盟友": "ALLIED_WITH",
            "所属": "MEMBER_OF",
            "成员": "MEMBER_OF",
            "弟子": "MEMBER_OF",
            "位于": "LOCATED_AT",
            "在": "LOCATED_AT",
            "拥有": "OWNS",
            "持有": "OWNS",
            "参与": "PARTICIPATED_IN",
            "参加": "PARTICIPATED_IN",
            "导致": "CAUSES",
            "引起": "CAUSES",
        }

        keyword_lower = keywords.lower()
        for key, value in relation_map.items():
            if key in keyword_lower:
                return value

        return "RELATED_TO"

    def _split_text(self, text: str, max_chunk_size: int = 2000) -> List[str]:
        """智能分段"""
        # 按段落分割
        paragraphs = re.split(r'\n\n+', text)

        result = []
        current = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(current) + len(para) < max_chunk_size:
                current += ("\n\n" if current else "") + para
            else:
                if current:
                    result.append(current)
                current = para

        if current:
            result.append(current)

        return result

    def _deduplicate_relations(
        self,
        relations: List[ExtractedRelation]
    ) -> List[ExtractedRelation]:
        """关系去重"""
        seen = set()
        unique = []

        for rel in relations:
            key = f"{rel.source}|{rel.target}|{rel.relation_type}"
            if key not in seen:
                seen.add(key)
                unique.append(rel)

        return unique
