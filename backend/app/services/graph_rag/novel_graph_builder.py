"""
小说图谱构建器

将抽取的实体和关系存储到 Neo4j 图数据库，并同步到 Qdrant 向量数据库
"""

import os
import json
import uuid
import logging
from typing import Dict, Any, List, Optional

from .novel_ontology_generator import Ontology, DEFAULT_NOVEL_ONTOLOGY
from .novel_entity_extractor import (
    NovelEntityExtractor,
    ExtractedEntity,
    ExtractedRelation,
    ExtractionResult
)

logger = logging.getLogger(__name__)


class NovelGraphBuilder:
    """
    小说图谱构建器

    负责将小说内容转换为知识图谱：
    1. 使用 LLM 生成本体定义
    2. 使用 GraphRAG 抽取实体和关系
    3. 存储到 Neo4j 图数据库
    4. 同步到 Qdrant 向量数据库
    """

    def __init__(self):
        from ..vector.qdrant_service import get_qdrant_service

        self.extractor = NovelEntityExtractor()
        self.qdrant = get_qdrant_service()
        self._neo4j_client = None

        logger.info("NovelGraphBuilder 初始化完成")

    @property
    def neo4j(self):
        """延迟加载 Neo4j 客户端"""
        if self._neo4j_client is None:
            try:
                from app.db.neo4j_client import get_neo4j_client
                self._neo4j_client = get_neo4j_client()
            except ImportError:
                logger.warning("Neo4j 客户端未安装，图谱将只存储到向量数据库")
        return self._neo4j_client

    def build(
        self,
        novel_id: str,
        text: str,
        ontology: Dict[str, Any] = None,
        enable_vector_index: bool = True
    ) -> ExtractionResult:
        """
        构建知识图谱

        Args:
            novel_id: 小说ID
            text: 小说文本
            ontology: 本体定义（可选）
            enable_vector_index: 是否创建向量索引

        Returns:
            抽取结果
        """
        logger.info(f"开始构建图谱: novel_id={novel_id}, text_length={len(text)}")

        # 1. 抽取实体和关系
        result = self.extractor.extract(text, ontology=ontology)

        if not result.entities:
            logger.warning("未抽取到任何实体")
            return result

        # 2. 存储到 Neo4j
        entity_id_map = self._store_to_neo4j(novel_id, result.entities, result.relations)

        # 3. 同步到 Qdrant
        if enable_vector_index:
            self._sync_to_qdrant(novel_id, result.entities, result.relations, entity_id_map)

        logger.info(f"图谱构建完成: {len(result.entities)} 个实体, {len(result.relations)} 个关系")

        return result

    def _store_to_neo4j(
        self,
        novel_id: str,
        entities: List[ExtractedEntity],
        relations: List[ExtractedRelation]
    ) -> Dict[str, str]:
        """
        存储到 Neo4j

        Returns:
            实体名称到ID的映射
        """
        entity_id_map = {}

        if not self.neo4j or not self.neo4j.is_available():
            logger.warning("Neo4j 不可用，跳过图存储")
            # 生成临时 ID
            for entity in entities:
                entity_id_map[entity.name] = str(uuid.uuid4())
            return entity_id_map

        # 创建实体节点
        for entity in entities:
            entity_id = str(uuid.uuid4())
            entity_id_map[entity.name] = entity_id

            # 构建 Cypher 查询
            label = self._get_neo4j_label(entity.entity_type)
            query = f"""
            MERGE (e:{label} {{novel_id: $novel_id, entity_id: $entity_id}})
            SET e.name = $name,
                e.description = $description,
                e.entity_type = $entity_type
            """

            params = {
                "novel_id": novel_id,
                "entity_id": entity_id,
                "name": entity.name,
                "description": entity.description,
                "entity_type": entity.entity_type
            }

            # 添加额外属性
            if entity.attributes:
                for key, value in entity.attributes.items():
                    if isinstance(value, (str, int, float, bool)):
                        query += f", e.{key} = ${key}"
                        params[key] = value
                    elif isinstance(value, (list, dict)):
                        query += f", e.{key} = ${key}"
                        params[key] = json.dumps(value, ensure_ascii=False)

            try:
                self.neo4j.execute_query(query, params)
            except Exception as e:
                logger.warning(f"创建实体节点失败 {entity.name}: {e}")

        # 创建关系边
        for relation in relations:
            source_id = entity_id_map.get(relation.source)
            target_id = entity_id_map.get(relation.target)

            if not source_id or not target_id:
                continue

            rel_type = self._sanitize_relation_type(relation.relation_type)
            query = f"""
            MATCH (source {{novel_id: $novel_id, entity_id: $source_id}})
            MATCH (target {{novel_id: $novel_id, entity_id: $target_id}})
            MERGE (source)-[r:{rel_type}]->(target)
            SET r.description = $description,
                r.strength = $strength
            """

            try:
                self.neo4j.execute_query(query, {
                    "novel_id": novel_id,
                    "source_id": source_id,
                    "target_id": target_id,
                    "description": relation.description,
                    "strength": relation.strength
                })
            except Exception as e:
                logger.warning(f"创建关系边失败 {relation.source}->{relation.target}: {e}")

        return entity_id_map

    def _sync_to_qdrant(
        self,
        novel_id: str,
        entities: List[ExtractedEntity],
        relations: List[ExtractedRelation],
        entity_id_map: Dict[str, str]
    ):
        """同步到 Qdrant 向量数据库"""
        # 同步实体
        for entity in entities:
            entity_id = entity_id_map.get(entity.name)
            if not entity_id:
                continue

            # 根据实体类型选择同步方法
            if entity.entity_type.lower() in ["character", "人物"]:
                self.qdrant.upsert_character(
                    novel_id=novel_id,
                    character_id=entity_id,
                    name=entity.name,
                    description=entity.description,
                    metadata={"entity_type": entity.entity_type}
                )
            else:
                # 其他类型作为文本索引
                self.qdrant.upsert_text(
                    novel_id=novel_id,
                    text_id=entity_id,
                    text=f"{entity.name}: {entity.description}",
                    metadata={
                        "name": entity.name,
                        "type": "entity",
                        "entity_type": entity.entity_type
                    }
                )

        # 同步关系（作为文本）
        for relation in relations:
            source_id = entity_id_map.get(relation.source)
            target_id = entity_id_map.get(relation.target)

            if not source_id or not target_id:
                continue

            relation_text = f"{relation.source} {relation.relation_type} {relation.target}: {relation.description}"
            self.qdrant.upsert_text(
                novel_id=novel_id,
                text_id=f"{source_id}_{target_id}",
                text=relation_text,
                metadata={
                    "type": "relation",
                    "source_id": source_id,
                    "target_id": target_id,
                    "relation_type": relation.relation_type,
                    "strength": relation.strength
                }
            )

    def _get_neo4j_label(self, entity_type: str) -> str:
        """获取 Neo4j 标签"""
        # 类型映射
        type_map = {
            "Character": "Character",
            "人物": "Character",
            "Location": "Location",
            "地点": "Location",
            "Organization": "Organization",
            "组织": "Organization",
            "Item": "Item",
            "物品": "Item",
            "Event": "Event",
            "事件": "Event",
            "Concept": "Concept",
            "概念": "Concept",
        }
        return type_map.get(entity_type, "Entity")

    def _sanitize_relation_type(self, relation_type: str) -> str:
        """标准化关系类型（Neo4j 要求大写字母开头）"""
        if not relation_type:
            return "RELATED_TO"

        # 替换特殊字符
        sanitized = relation_type.upper()
        sanitized = sanitized.replace("-", "_").replace(" ", "_")

        # 确保字母开头
        if not sanitized[0].isalpha():
            sanitized = "REL_" + sanitized

        return sanitized

    def get_graph_summary(self, novel_id: str) -> Dict[str, Any]:
        """
        获取图谱摘要

        Args:
            novel_id: 小说ID

        Returns:
            图谱摘要信息
        """
        summary = {
            "novel_id": novel_id,
            "entity_count": 0,
            "relation_count": 0,
            "entity_types": {},
            "relation_types": {}
        }

        if not self.neo4j or not self.neo4j.is_available():
            return summary

        # 统计实体数量
        entity_query = """
        MATCH (e {novel_id: $novel_id})
        RETURN e.entity_type as type, count(e) as count
        """
        try:
            results = self.neo4j.execute_query(entity_query, {"novel_id": novel_id})
            for r in results:
                entity_type = r.get("type", "Unknown")
                count = r.get("count", 0)
                summary["entity_types"][entity_type] = count
                summary["entity_count"] += count
        except Exception as e:
            logger.warning(f"统计实体失败: {e}")

        # 统计关系数量
        relation_query = """
        MATCH (n)-[r]-(m)
        WHERE n.novel_id = $novel_id AND m.novel_id = $novel_id
          AND elementId(n) < elementId(m)
        RETURN type(r) as type, count(r) as count
        """
        try:
            results = self.neo4j.execute_query(relation_query, {"novel_id": novel_id})
            for r in results:
                rel_type = r.get("type", "Unknown")
                count = r.get("count", 0)
                summary["relation_types"][rel_type] = count
                summary["relation_count"] += count
        except Exception as e:
            logger.warning(f"统计关系失败: {e}")

        return summary
