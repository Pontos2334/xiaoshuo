"""
Qdrant 向量数据库服务

提供向量存储和语义搜索功能
"""

import uuid
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

from app.core.config import settings
from .embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class QdrantVectorService:
    """
    Qdrant 向量数据库服务

    提供向量存储和语义搜索功能，用于小说内容的语义检索
    """

    def __init__(
        self,
        url: str = None,
        embedding_service: EmbeddingService = None
    ):
        """
        初始化 Qdrant 服务

        Args:
            url: Qdrant 服务 URL (默认: http://localhost:6333)
            embedding_service: Embedding 服务实例
        """
        self.url = url or settings.QDRANT_URL

        try:
            self.client = QdrantClient(
                url=self.url,
                timeout=30,
                check_compatibility=False
            )
            logger.info(f"QdrantVectorService 初始化完成: {self.url}")
        except Exception as e:
            logger.warning(f"Qdrant 连接失败: {e}，服务将返回空结果")
            self.client = None

        self.embedding = embedding_service or EmbeddingService()

    def _get_collection_name(self, novel_id: str) -> str:
        """
        获取小说对应的集合名称

        Args:
            novel_id: 小说ID

        Returns:
            集合名称 (安全的格式)
        """
        safe_name = novel_id.replace("-", "_").replace("/", "_")
        return f"novel_{safe_name}"

    def ensure_collection(self, novel_id: str) -> str:
        """
        确保集合存在

        Args:
            novel_id: 小说ID

        Returns:
            集合名称
        """
        if not self.client:
            logger.warning("Qdrant 客户端未初始化")
            return ""

        collection_name = self._get_collection_name(novel_id)

        try:
            # 检查集合是否存在
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]

            if collection_name not in collection_names:
                # 动态获取向量维度
                vector_size = self.embedding.get_vector_size()
                # 创建新集合
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=vector_size,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"创建 Qdrant 集合: {collection_name} (维度: {vector_size})")

            return collection_name
        except Exception as e:
            logger.error(f"确保集合存在失败: {e}")
            return ""

    def upsert_character(
        self,
        novel_id: str,
        character_id: str,
        name: str,
        description: str,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """
        添加/更新人物向量

        Args:
            novel_id: 小说ID
            character_id: 人物ID
            name: 人物名称
            description: 人物描述
            metadata: 元数据

        Returns:
            是否成功
        """
        if not self.client:
            return False

        collection_name = self.ensure_collection(novel_id)
        if not collection_name:
            return False

        # 构建索引文本
        text = f"{name}: {description}" if description else name

        # 生成嵌入
        vector = self.embedding.embed(text)

        # 准备元数据
        payload = {
            "uuid": character_id,
            "text": text,
            "name": name,
            "type": "character",
            "created_at": datetime.now().isoformat(),
            **(metadata or {})
        }

        try:
            self.client.upsert(
                collection_name=collection_name,
                points=[
                    PointStruct(
                        id=character_id,
                        vector=vector,
                        payload=payload
                    )
                ]
            )
            return True
        except Exception as e:
            logger.error(f"上传人物向量失败: {e}")
            return False

    def upsert_plot(
        self,
        novel_id: str,
        plot_id: str,
        title: str,
        summary: str,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """
        添加/更新情节向量

        Args:
            novel_id: 小说ID
            plot_id: 情节ID
            title: 情节标题
            summary: 情节概述
            metadata: 元数据

        Returns:
            是否成功
        """
        if not self.client:
            return False

        collection_name = self.ensure_collection(novel_id)
        if not collection_name:
            return False

        # 构建索引文本
        text = f"{title}: {summary}" if summary else title

        # 生成嵌入
        vector = self.embedding.embed(text)

        # 准备元数据
        payload = {
            "uuid": plot_id,
            "text": text,
            "title": title,
            "type": "plot",
            "created_at": datetime.now().isoformat(),
            **(metadata or {})
        }

        try:
            self.client.upsert(
                collection_name=collection_name,
                points=[
                    PointStruct(
                        id=plot_id,
                        vector=vector,
                        payload=payload
                    )
                ]
            )
            return True
        except Exception as e:
            logger.error(f"上传情节向量失败: {e}")
            return False

    def upsert_text(
        self,
        novel_id: str,
        text_id: str,
        text: str,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """
        添加/更新文本条目向量

        用于索引小说片段

        Args:
            novel_id: 小说ID
            text_id: 文本ID
            text: 文本内容
            metadata: 元数据

        Returns:
            是否成功
        """
        if not self.client:
            return False

        collection_name = self.ensure_collection(novel_id)
        if not collection_name:
            return False

        # 生成嵌入
        vector = self.embedding.embed(text)

        # 准备元数据
        payload = {
            "uuid": text_id,
            "text": text,
            "type": "text",
            "created_at": datetime.now().isoformat(),
            **(metadata or {})
        }

        try:
            self.client.upsert(
                collection_name=collection_name,
                points=[
                    PointStruct(
                        id=text_id,
                        vector=vector,
                        payload=payload
                    )
                ]
            )
            return True
        except Exception as e:
            logger.error(f"上传文本向量失败: {e}")
            return False

    def search(
        self,
        novel_id: str,
        query: str,
        limit: int = 10,
        item_type: str = None
    ) -> List[Dict[str, Any]]:
        """
        语义搜索

        Args:
            novel_id: 小说ID
            query: 查询文本
            limit: 返回数量
            item_type: 过滤类型 (character/plot/text)

        Returns:
            搜索结果列表，每项包含 id, text, score, type, payload
        """
        if not self.client:
            return []

        collection_name = self._get_collection_name(novel_id)

        try:
            # 检查集合是否存在
            collections = self.client.get_collections().collections
            if collection_name not in [c.name for c in collections]:
                logger.warning(f"集合不存在: {collection_name}")
                return []

            # 生成查询向量
            query_vector = self.embedding.embed(query)

            # 构建过滤条件
            query_filter = None
            if item_type:
                query_filter = Filter(
                    must=[
                        FieldCondition(
                            key="type",
                            match=MatchValue(value=item_type)
                        )
                    ]
                )

            # 执行搜索
            results = self.client.query_points(
                collection_name=collection_name,
                query=query_vector,
                limit=limit,
                query_filter=query_filter
            )

            # 格式化结果
            formatted_results = []
            for result in results.points:
                formatted_results.append({
                    "id": result.id,
                    "text": result.payload.get("text", ""),
                    "score": result.score,
                    "type": result.payload.get("type", "unknown"),
                    "name": result.payload.get("name", result.payload.get("title", "")),
                    "payload": result.payload
                })

            return formatted_results

        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return []

    def search_characters(
        self,
        novel_id: str,
        query: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        搜索相似人物

        Args:
            novel_id: 小说ID
            query: 查询文本
            limit: 返回数量

        Returns:
            人物列表
        """
        return self.search(novel_id, query, limit, item_type="character")

    def search_plots(
        self,
        novel_id: str,
        query: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        搜索相似情节

        Args:
            novel_id: 小说ID
            query: 查询文本
            limit: 返回数量

        Returns:
            情节列表
        """
        return self.search(novel_id, query, limit, item_type="plot")

    def delete_collection(self, novel_id: str) -> bool:
        """
        删除小说对应的集合

        Args:
            novel_id: 小说ID

        Returns:
            是否成功
        """
        if not self.client:
            return False

        collection_name = self._get_collection_name(novel_id)

        try:
            self.client.delete_collection(collection_name=collection_name)
            logger.info(f"删除集合: {collection_name}")
            return True
        except Exception as e:
            logger.warning(f"删除集合失败: {e}")
            return False

    def delete_point(self, novel_id: str, point_id: str) -> bool:
        """
        删除单个向量点

        Args:
            novel_id: 小说ID
            point_id: 点ID

        Returns:
            是否成功
        """
        if not self.client:
            return False

        collection_name = self._get_collection_name(novel_id)

        try:
            self.client.delete(
                collection_name=collection_name,
                points_selector=[point_id]
            )
            return True
        except Exception as e:
            logger.warning(f"删除向量点失败: {e}")
            return False


# 单例实例
_qdrant_service: Optional[QdrantVectorService] = None


def get_qdrant_service() -> QdrantVectorService:
    """获取 Qdrant 服务单例"""
    global _qdrant_service
    if _qdrant_service is None:
        _qdrant_service = QdrantVectorService()
    return _qdrant_service
