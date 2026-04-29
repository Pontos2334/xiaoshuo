"""
共享 LLM 客户端工厂

统一管理 DeepSeek API（OpenAI SDK 兼容）客户端实例，避免各服务重复创建
"""

import asyncio
import logging
from typing import Optional
from openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMClientFactory:
    """LLM 客户端工厂（单例模式）"""

    _instance: Optional["LLMClientFactory"] = None
    _client: Optional[OpenAI] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_client()
        return cls._instance

    def _init_client(self):
        if settings.DEEPSEEK_API_KEY:
            self._client = OpenAI(
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=settings.DEEPSEEK_BASE_URL,
            )
            logger.info(f"LLM 客户端初始化: model={settings.DEEPSEEK_MODEL}, base_url={settings.DEEPSEEK_BASE_URL}")
        else:
            self._client = None
            logger.warning("未配置 DEEPSEEK_API_KEY")

    @property
    def client(self) -> Optional[OpenAI]:
        return self._client

    @property
    def model(self) -> str:
        return settings.DEEPSEEK_MODEL

    @property
    def max_tokens(self) -> int:
        return settings.MAX_TOKENS

    @property
    def is_available(self) -> bool:
        return self._client is not None

    def generate_sync(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """同步生成"""
        if not self._client:
            raise RuntimeError("LLM 客户端未初始化")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        else:
            messages.append({"role": "system", "content": "你是一位专业的小说创作顾问，擅长分析文学作品和提供创作建议。请用中文回答。"})
        messages.append({"role": "user", "content": prompt})

        response = self._client.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=messages,
            extra_body={"thinking": {"type": "enabled"}},
        )
        return response.choices[0].message.content

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """异步生成（使用 asyncio.to_thread 避免阻塞事件循环）"""
        return await asyncio.to_thread(self.generate_sync, prompt, system_prompt)


# 全局单例
llm_factory = LLMClientFactory()
