"""
应用配置

使用 Pydantic Settings 管理环境变量配置
"""

import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import field_validator


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

    # Qdrant 配置
    QDRANT_URL: str = "http://localhost:6333"

    # AI 配置
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_BASE_URL: str = "https://api.anthropic.com"
    CLAUDE_MODEL: str = "claude-sonnet-4-6"
    MAX_TOKENS: int = 4096

    # Embedding 配置
    EMBEDDING_USE_LOCAL: bool = False
    EMBEDDING_LOCAL_MODEL: str = "paraphrase-multilingual-MiniLM-L12-v2"

    # GraphRAG 配置
    GRAPH_RAG_MAX_GLEANINGS: int = 1
    GRAPH_RAG_CHUNK_SIZE: int = 2000

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
        return origins

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# 全局配置实例
settings = Settings()
