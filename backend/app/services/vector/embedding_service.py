"""
Embedding 服务

支持：
1. 云端 API (OpenAI/阿里云/智谱AI)
2. 本地模型 (sentence-transformers)
"""

import os
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Embedding 服务

    支持云端 API 和本地模型两种模式
    """

    def __init__(
        self,
        api_key: str = None,
        base_url: str = None,
        model: str = None,
        use_local: bool = None,
        local_model_path: str = None
    ):
        """
        初始化 Embedding 服务

        Args:
            api_key: API Key (云端模式需要)
            base_url: API Base URL (云端模式需要)
            model: 模型名称 (云端模式)
            use_local: 是否使用本地模型
            local_model_path: 本地模型路径
        """
        # 从环境变量读取配置
        self.use_local = use_local if use_local is not None else (
            os.getenv('EMBEDDING_USE_LOCAL', 'false').lower() == 'true'
        )
        self.local_model_path = local_model_path or os.getenv(
            'EMBEDDING_LOCAL_MODEL',
            'paraphrase-multilingual-MiniLM-L12-v2'
        )

        if self.use_local:
            self._init_local_model()
        else:
            # 云端模式
            from openai import OpenAI

            self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
            self.base_url = base_url or os.getenv('EMBEDDING_BASE_URL', os.getenv('ANTHROPIC_BASE_URL'))
            self.model = model or os.getenv('EMBEDDING_MODEL', 'text-embedding-v3')

            if self.api_key:
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                    timeout=60.0
                )
                logger.info(f"EmbeddingService 初始化完成 (云端): model={self.model}")
            else:
                logger.warning("未配置 API Key，Embedding 服务将返回空向量")
                self.client = None

    def _init_local_model(self):
        """初始化本地 sentence-transformers 模型"""
        try:
            from sentence_transformers import SentenceTransformer

            logger.info(f"正在加载本地 embedding 模型: {self.local_model_path}")
            self.local_model = SentenceTransformer(self.local_model_path)
            self.vector_size = self.local_model.get_sentence_embedding_dimension()
            logger.info(f"本地 embedding 模型加载完成: vector_size={self.vector_size}")
        except ImportError:
            logger.error("sentence_transformers 未安装，请运行: pip install sentence-transformers")
            raise
        except Exception as e:
            logger.error(f"本地模型加载失败: {e}")
            raise

    def embed(self, text: str) -> List[float]:
        """
        生成文本嵌入

        Args:
            text: 输入文本

        Returns:
            嵌入向量
        """
        if self.use_local:
            return self._embed_local(text)
        else:
            return self._embed_remote(text)

    def _embed_local(self, text: str) -> List[float]:
        """使用本地模型生成嵌入"""
        try:
            embedding = self.local_model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"本地模型生成嵌入失败: {e}")
            return [0.0] * self.vector_size

    def _embed_remote(self, text: str) -> List[float]:
        """使用云端 API 生成嵌入"""
        if not self.client:
            logger.warning("API 客户端未初始化，返回空向量")
            return [0.0] * 1024

        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"云端 API 生成嵌入失败: {e}")
            # 根据模型返回对应维度的零向量
            dim = 1024 if "embedding-v3" in self.model or "embedding-v" in self.model else 1536
            return [0.0] * dim

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        批量生成嵌入

        Args:
            texts: 输入文本列表

        Returns:
            嵌入向量列表
        """
        if self.use_local:
            return self._embed_batch_local(texts)
        else:
            return self._embed_batch_remote(texts)

    def _embed_batch_local(self, texts: List[str]) -> List[List[float]]:
        """使用本地模型批量生成嵌入"""
        try:
            embeddings = self.local_model.encode(texts, convert_to_numpy=True)
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"本地模型批量生成嵌入失败: {e}")
            return [[0.0] * self.vector_size for _ in texts]

    def _embed_batch_remote(self, texts: List[str]) -> List[List[float]]:
        """使用云端 API 批量生成嵌入"""
        if not self.client:
            return [[0.0] * 1024 for _ in texts]

        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=texts
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"云端 API 批量生成嵌入失败: {e}")
            dim = 1024 if "embedding-v3" in self.model or "embedding-v" in self.model else 1536
            return [[0.0] * dim for _ in texts]

    def get_vector_size(self) -> int:
        """获取向量维度"""
        if self.use_local:
            return self.vector_size
        else:
            # 云端模型维度
            model = self.model
            if "embedding-v3" in model or "embedding-v" in model:
                return 1024
            elif "text-embedding-3-large" in model:
                return 3072
            elif "text-embedding-3-small" in model:
                return 1536
            else:
                return 1536
