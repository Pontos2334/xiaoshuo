import uuid
from typing import List, Dict, Any, Optional
from app.db.neo4j_client import neo4j_client
import logging

logger = logging.getLogger(__name__)


class BaseRepository:
    """基础仓库类"""

    def __init__(self, label: str):
        self.label = label

    def _generate_id(self) -> str:
        return str(uuid.uuid4())

    def _node_to_dict(self, node) -> Dict:
        """将 Neo4j 节点转换为字典"""
        if not node:
            return {}
        return dict(node)


class CharacterRepository(BaseRepository):
    """人物仓库"""

    def __init__(self):
        super().__init__("Character")

    def get_by_novel(self, novel_id: str) -> List[Dict]:
        """获取小说的所有人物"""
        query = f"""
        MATCH (n:Novel {{id: $novel_id}})-[:HAS_CHARACTER]->(c:{self.label})
        RETURN c
        ORDER BY c.name
        """
        results = neo4j_client.run(query, {"novel_id": novel_id})
        return [self._node_to_dict(r["c"]) for r in results]

    def get_by_id(self, character_id: str) -> Optional[Dict]:
        """获取单个人物"""
        query = f"MATCH (c:{self.label} {{id: $id}}) RETURN c LIMIT 1"
        result = neo4j_client.run_single(query, {"id": character_id})
        return self._node_to_dict(result["c"]) if result else None

    def create(self, novel_id: str, data: Dict) -> Optional[Dict]:
        """创建人物节点并关联到小说"""
        char_id = self._generate_id()
        query = f"""
        MATCH (n:Novel {{id: $novel_id}})
        CREATE (c:{self.label} {{
            id: $id,
            name: $name,
            aliases: $aliases,
            basic_info: $basic_info,
            personality: $personality,
            abilities: $abilities,
            story_summary: $story_summary,
            first_appear: $first_appear
        }})
        CREATE (n)-[:HAS_CHARACTER]->(c)
        RETURN c
        """
        params = {
            "novel_id": novel_id,
            "id": char_id,
            "name": data.get("name", ""),
            "aliases": data.get("aliases", []),
            "basic_info": data.get("basic_info", data.get("basicInfo", {})),
            "personality": data.get("personality", []),
            "abilities": data.get("abilities", []),
            "story_summary": data.get("story_summary", data.get("storySummary", "")),
            "first_appear": data.get("first_appear", data.get("firstAppear", "")),
        }
        result = neo4j_client.run_single(query, params)
        return self._node_to_dict(result["c"]) if result else None

    def update(self, character_id: str, data: Dict) -> Optional[Dict]:
        """更新人物"""
        if not data:
            return None

        set_parts = []
        params = {"id": character_id}

        field_mapping = {
            "name": "name",
            "aliases": "aliases",
            "basic_info": "basic_info",
            "basicInfo": "basic_info",
            "personality": "personality",
            "abilities": "abilities",
            "story_summary": "story_summary",
            "storySummary": "story_summary",
            "first_appear": "first_appear",
            "firstAppear": "first_appear",
        }

        for key, value in data.items():
            if key in field_mapping:
                field_name = field_mapping[key]
                set_parts.append(f"c.{field_name} = ${field_name}")
                params[field_name] = value

        if not set_parts:
            return self.get_by_id(character_id)

        query = f"""
        MATCH (c:{self.label} {{id: $id}})
        SET {', '.join(set_parts)}
        RETURN c
        """
        result = neo4j_client.run_single(query, params)
        return self._node_to_dict(result["c"]) if result else None

    def delete(self, character_id: str) -> bool:
        """删除人物"""
        query = f"""
        MATCH (c:{self.label} {{id: $id}})
        DETACH DELETE c
        """
        try:
            neo4j_client.run(query, {"id": character_id})
            return True
        except Exception as e:
            logger.error(f"删除人物失败: {e}")
            return False


class CharacterRelationRepository(BaseRepository):
    """人物关系仓库"""

    def __init__(self):
        super().__init__("CharacterRelation")

    def get_by_novel(self, novel_id: str) -> List[Dict]:
        """获取小说的所有人物关系"""
        query = """
        MATCH (n:Novel {id: $novel_id})-[:HAS_CHARACTER]->(c:Character)
        MATCH (c)-[rel:RELATED_TO]->(c2:Character)
        WHERE (n)-[:HAS_CHARACTER]->(c) AND (n)-[:HAS_CHARACTER]->(c2)
        RETURN {
            id: elementId(rel),
            source_id: c.id,
            target_id: c2.id,
            relation_type: rel.type,
            description: rel.description,
            strength: rel.strength
        }
        """
        results = neo4j_client.run(query, {"novel_id": novel_id})
        return [
            {
                "id": r["id"],
                "sourceId": r["source_id"],
                "targetId": r["target_id"],
                "relationType": r["relation_type"],
                "description": r["description"],
                "strength": r["strength"],
            }
            for r in results
        ]

    def create(self, novel_id: str, source_id: str, target_id: str, data: Dict) -> Optional[Dict]:
        """创建人物关系"""
        rel_id = self._generate_id()
        query = """
        MATCH (c1:Character {id: $source_id})
        MATCH (c2:Character {id: $target_id})
        CREATE (c1)-[:RELATED_TO {
            id: $rel_id,
            type: $type,
            description: $description,
            strength: $strength
        }]->(c2)
        RETURN elementId(relationship) as id
        """
        params = {
            "source_id": source_id,
            "target_id": target_id,
            "rel_id": rel_id,
            "type": data.get("relation_type", data.get("relationType", "关联")),
            "description": data.get("description", ""),
            "strength": data.get("strength", 5),
        }
        try:
            result = neo4j_client.run_single(query, params)
            if result:
                return {
                    "id": rel_id,
                    "sourceId": source_id,
                    "targetId": target_id,
                    "relationType": params["type"],
                    "description": params["description"],
                    "strength": params["strength"],
                }
            return None
        except Exception as e:
            logger.error(f"创建关系失败: {e}")
            return None

    def update(self, relation_id: str, data: Dict) -> Optional[Dict]:
        """更新关系"""
        set_parts = []
        params = {"rel_id": relation_id}

        field_mapping = {
            "relation_type": "type",
            "relationType": "type",
            "description": "description",
            "strength": "strength",
        }

        for key, value in data.items():
            if key in field_mapping:
                field_name = field_mapping[key]
                set_parts.append(f"rel.{field_name} = ${field_name}")
                params[field_name] = value

        if not set_parts:
            return None

        query = f"""
        MATCH ()-[rel:RELATED_TO]->()
        WHERE elementId(rel) = $rel_id
        SET {', '.join(set_parts)}
        RETURN elementId(rel) as id
        """
        try:
            neo4j_client.run_single(query, params)
            return {"id": relation_id, **data}
        except Exception as e:
            logger.error(f"更新关系失败: {e}")
            return None

    def delete(self, relation_id: str) -> bool:
        """删除关系"""
        query = """
        MATCH ()-[rel:RELATED_TO]->()
        WHERE elementId(rel) = $rel_id
        DELETE rel
        """
        try:
            neo4j_client.run(query, {"rel_id": relation_id})
            return True
        except Exception as e:
            logger.error(f"删除关系失败: {e}")
            return False


class NovelRepository(BaseRepository):
    """小说仓库"""

    def __init__(self):
        super().__init__("Novel")

    def get_by_id(self, novel_id: str) -> Optional[Dict]:
        """获取小说"""
        query = f"MATCH (n:{self.label} {{id: $id}}) RETURN n LIMIT 1"
        result = neo4j_client.run_single(query, {"id": novel_id})
        return self._node_to_dict(result["n"]) if result else None

    def create(self, data: Dict) -> Optional[Dict]:
        """创建小说节点"""
        novel_id = self._generate_id()
        query = f"""
        CREATE (n:{self.label} {{
            id: $id,
            name: $name,
            path: $path,
            content_path: $content_path,
            chapter_count: $chapter_count,
            word_count: $word_count
        }})
        RETURN n
        """
        params = {
            "id": novel_id,
            "name": data.get("name", ""),
            "path": data.get("path", ""),
            "content_path": data.get("content_path", data.get("contentPath", "")),
            "chapter_count": data.get("chapter_count", data.get("chapterCount", 0)),
            "word_count": data.get("word_count", data.get("wordCount", 0)),
        }
        result = neo4j_client.run_single(query, params)
        return self._node_to_dict(result["n"]) if result else None


# 全局仓库实例
character_repo = CharacterRepository()
character_relation_repo = CharacterRelationRepository()
novel_repo = NovelRepository()
