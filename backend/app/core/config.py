"""
应用配置

使用 Pydantic Settings 管理环境变量配置
"""

import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import field_validator, ConfigDict


class Settings(BaseSettings):
    """应用配置类"""

    # API 配置
    API_PORT: int = 8002
    API_HOST: str = "0.0.0.0"

    # 前端配置
    FRONTEND_URL: str = "http://localhost:3000"

    # 数据库配置
    DATABASE_URL: str = "sqlite:///./novel_assistant.db"

    # Neo4j 配置
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = ""
    NEO4J_ENABLED: bool = False  # 是否启用 Neo4j（SQLite 为主数据源）

    # Qdrant 配置
    QDRANT_URL: str = "http://localhost:6333"

    # AI 配置 (DeepSeek)
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    MAX_TOKENS: int = 4096
    DEEPSEEK_REASONING_EFFORT: str = "max"  # 思考强度: high / max（默认 max 最强思考）

    # Embedding 配置
    EMBEDDING_USE_LOCAL: bool = False
    EMBEDDING_LOCAL_MODEL: str = "paraphrase-multilingual-MiniLM-L12-v2"

    # CORS 额外允许的源（逗号分隔，用于 Docker/生产部署）
    CORS_ORIGINS: str = ""

    # GraphRAG 配置
    GRAPH_RAG_MAX_GLEANINGS: int = 1
    GRAPH_RAG_CHUNK_SIZE: int = 2000

    # 安全配置
    API_KEY: str = ""  # 可选的 API Key 认证，为空则不启用
    SCAN_ALLOWED_ROOTS: str = ""  # 允许扫描的根目录（逗号分隔），为空则不限制（仅开发模式）

    # 长文本处理配置
    LONG_TEXT_THRESHOLD: int = 15000      # 触发 Map-Reduce 的字符阈值
    MAP_REDUCE_MAX_CONCURRENT: int = 3    # 最大并发任务数
    CHUNK_SIZE_CHARACTER: int = 3000      # 人物分析块大小
    CHUNK_SIZE_PLOT: int = 4000           # 情节分析块大小
    CHUNK_OVERLAP_SIZE: int = 200         # 块重叠大小

    @field_validator("FRONTEND_URL", mode="before")
    @classmethod
    def validate_frontend_url(cls, v: str) -> str:
        """验证前端 URL"""
        if v and not v.startswith("http"):
            return f"http://{v}"
        return v

    @property
    def allowed_cors_origins(self) -> List[str]:
        """获取允许的 CORS 源"""
        origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
        if self.FRONTEND_URL and self.FRONTEND_URL not in origins:
            origins.append(self.FRONTEND_URL)
        if self.CORS_ORIGINS:
            for origin in self.CORS_ORIGINS.split(","):
                origin = origin.strip()
                if origin and origin not in origins:
                    origins.append(origin)
        return origins

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


# 全局配置实例
settings = Settings()
