"""
共享 LLM 客户端（兼容层）

保留此文件以兼容现有导入，实际逻辑已合并到 agent/client.py
"""

from app.agent.client import AIAgentClient, get_ai_client

# 兼容旧代码的工厂类
class LLMClientFactory:
    """LLM 客户端工厂（兼容层，已弃用，请直接使用 get_ai_client()）"""

    @property
    def client(self):
        return get_ai_client().client

    @property
    def model(self):
        return get_ai_client().model

    @property
    def max_tokens(self):
        return get_ai_client().max_tokens

    @property
    def is_available(self):
        return get_ai_client().is_available

    def generate_sync(self, prompt, system_prompt=None):
        return get_ai_client().generate_sync(prompt, system_prompt)

    async def generate(self, prompt, system_prompt=None):
        return await get_ai_client().generate(prompt, system_prompt)


# 全局单例（兼容）
llm_factory = LLMClientFactory()
