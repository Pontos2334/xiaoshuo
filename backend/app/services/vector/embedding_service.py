"""
Embedding 服务

支持：
1. 云端 API (OpenAI/阿里云/智谱AI)
2. 本地模型 (sentence-transformers)
"""

import logging
from typing import List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# 重试装饰器
def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 10.0):
    """简单的重试装饰器，避免引入额外依赖"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            import time
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        logger.warning(f"Embedding 调用失败 (尝试 {attempt + 1}/{max_retries})，{delay}秒后重试: {e}")
                        time.sleep(delay)
            raise last_exception
        return wrapper
    return decorator


class EmbeddingService:
    """
    Embedding 服务

    支持云端 API 和本地模型两种模式
    """

    # 重试配置
    MAX_RETRIES = 3
    RETRY_BASE_DELAY = 1.0
    RETRY_MAX_DELAY = 10.0

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
        # 从配置读取
        self.use_local = use_local if use_local is not None else settings.EMBEDDING_USE_LOCAL
        self.local_model_path = local_model_path or settings.EMBEDDING_LOCAL_MODEL

        if self.use_local:
            self._init_local_model()
        else:
            # 云端模式
            from openai import OpenAI

            self.api_key = api_key or settings.ANTHROPIC_API_KEY
            self.base_url = base_url or settings.ANTHROPIC_BASE_URL
            self.model = model or 'text-embedding-v3'

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
            raise  # 本地模型失败应该抛出异常，不静默返回

    @retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=10.0)
    def _embed_remote(self, text: str) -> List[float]:
        """使用云端 API 生成嵌入（带重试）"""
        if not self.client:
            raise RuntimeError("API 客户端未初始化")

        response = self.client.embeddings.create(
            model=self.model,
            input=text
        )
        return response.data[0].embedding

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
            raise

    @retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=10.0)
    def _embed_batch_remote(self, texts: List[str]) -> List[List[float]]:
        """使用云端 API 批量生成嵌入（带重试）"""
        if not self.client:
            raise RuntimeError("API 客户端未初始化")

        response = self.client.embeddings.create(
            model=self.model,
            input=texts
        )
        return [item.embedding for item in response.data]

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

    def health_check(self) -> dict:
        """
        健康检查

        Returns:
            包含状态信息的字典
        """
        try:
            test_embedding = self.embed("test")
            return {
                "status": "healthy",
                "mode": "local" if self.use_local else "remote",
                "vector_size": len(test_embedding),
                "model": self.local_model_path if self.use_local else self.model
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "mode": "local" if self.use_local else "remote"
            }
