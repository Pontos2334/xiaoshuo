import os
import asyncio
import logging
import json
from typing import Optional
from datetime import datetime
from app.core.config import settings
from openai import OpenAI

logger = logging.getLogger(__name__)


class AIAgentClient:
    """
    统一的 AI Agent 客户端（单例模式）

    基于 DeepSeek API（OpenAI SDK 兼容），提供同步/异步生成能力。
    所有服务共享同一个客户端实例。
    """

    _instance: Optional["AIAgentClient"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self.api_key = settings.DEEPSEEK_API_KEY
        self.base_url = settings.DEEPSEEK_BASE_URL
        self.model = settings.DEEPSEEK_MODEL
        self.max_tokens = settings.MAX_TOKENS
        self.reasoning_effort = settings.DEEPSEEK_REASONING_EFFORT

        # 日志保存目录
        self.log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "llm")
        os.makedirs(self.log_dir, exist_ok=True)

        if self.api_key:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            logger.info(f"AI 客户端初始化完成: model={self.model}, base_url={self.base_url}")
        else:
            self.client = None
            logger.warning("未配置 DEEPSEEK_API_KEY，将使用模拟响应")

    @property
    def is_available(self) -> bool:
        return self.client is not None

    def _save_llm_log(self, prompt: str, response: str, error: Optional[str] = None, metadata: dict = None):
        """保存 LLM 调用日志"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = os.path.join(self.log_dir, f"llm_call_{timestamp}.json")

            log_data = {
                "timestamp": datetime.now().isoformat(),
                "model": self.model,
                "base_url": self.base_url,
                "prompt_preview": prompt[:500] + "..." if len(prompt) > 500 else prompt,
                "prompt_length": len(prompt),
                "response_preview": response[:500] + "..." if response and len(response) > 500 else response,
                "response_length": len(response) if response else 0,
                "error": error,
                "metadata": metadata or {}
            }

            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, ensure_ascii=False, indent=2)

            logger.debug(f"LLM 调用日志已保存: {log_file}")
        except Exception as e:
            logger.warning(f"保存 LLM 日志失败: {e}")

    def _build_messages(self, prompt: str, system_prompt: Optional[str] = None) -> list:
        """构建消息列表"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        else:
            messages.append({"role": "system", "content": "你是一位专业的小说创作顾问，擅长分析文学作品和提供创作建议。请用中文回答。"})
        messages.append({"role": "user", "content": prompt})
        return messages

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """生成响应（异步，使用 asyncio.to_thread 避免阻塞事件循环）"""
        if not self.client:
            return self._demo_response(prompt)

        try:
            logger.info(f"调用 LLM: model={self.model}, prompt_length={len(prompt)}")
            messages = self._build_messages(prompt, system_prompt)

            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model,
                max_tokens=self.max_tokens,
                messages=messages,
                timeout=120.0,
                extra_body={"thinking": {"type": "enabled"}}
            )

            if not response.choices or response.choices[0].message.content is None:
                raise RuntimeError("API 返回空响应或内容为 null")

            response_text = response.choices[0].message.content
            reasoning_content = getattr(response.choices[0].message, 'reasoning_content', None)

            logger.info(f"LLM 响应成功: response_length={len(response_text)}, reasoning_length={len(reasoning_content) if reasoning_content else 0}")

            self._save_llm_log(
                prompt=prompt,
                response=response_text,
                metadata={
                    "reasoning_content": reasoning_content[:500] + "..." if reasoning_content and len(reasoning_content) > 500 else reasoning_content,
                    "reasoning_length": len(reasoning_content) if reasoning_content else 0,
                    "usage": {
                        "input_tokens": response.usage.prompt_tokens if response.usage else None,
                        "output_tokens": response.usage.completion_tokens if response.usage else None
                    }
                }
            )

            return response_text

        except Exception as e:
            error_msg = f"API 调用错误: {type(e).__name__}: {e}"
            logger.error(error_msg)
            self._save_llm_log(prompt=prompt, response=None, error=error_msg, metadata={"error_type": type(e).__name__})
            raise RuntimeError(error_msg) from e

    def generate_sync(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """同步生成响应"""
        if not self.client:
            return self._demo_response(prompt)

        try:
            logger.info(f"调用 LLM (sync): model={self.model}, prompt_length={len(prompt)}")
            messages = self._build_messages(prompt, system_prompt)

            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=messages,
                timeout=120.0,
                extra_body={"thinking": {"type": "enabled"}}
            )

            if not response.choices or response.choices[0].message.content is None:
                raise RuntimeError("API 返回空响应或内容为 null")

            response_text = response.choices[0].message.content
            reasoning_content = getattr(response.choices[0].message, 'reasoning_content', None)
            logger.info(f"LLM 响应成功 (sync): response_length={len(response_text)}, reasoning_length={len(reasoning_content) if reasoning_content else 0}")

            self._save_llm_log(
                prompt=prompt,
                response=response_text,
                metadata={
                    "reasoning_length": len(reasoning_content) if reasoning_content else 0
                }
            )

            return response_text

        except Exception as e:
            error_msg = f"API 调用错误: {type(e).__name__}: {e}"
            logger.error(error_msg)
            self._save_llm_log(prompt=prompt, response=None, error=error_msg)
            raise RuntimeError(error_msg) from e

    def _demo_response(self, prompt: str) -> str:
        """演示/开发用响应（仅在未配置 API key 时使用）"""
        logger.info("使用模拟响应")
        if "人物" in prompt or "角色" in prompt:
            return '''```json
[
  {
    "name": "李云",
    "aliases": ["小李", "云少"],
    "basic_info": {"年龄": "18岁", "性别": "男", "身份": "山村少年"},
    "personality": ["勇敢", "善良", "好奇心强", "有时冲动"],
    "abilities": ["剑心通明", "剑术天赋"],
    "story_summary": "普通山村少年，因救了神秘女子苏瑶而踏上冒险之路，展现出惊人的剑道天赋。",
    "first_appear": "第一章"
  },
  {
    "name": "苏瑶",
    "aliases": ["天机圣女", "神秘女子"],
    "basic_info": {"年龄": "20岁", "性别": "女", "身份": "天机阁圣女"},
    "personality": ["外冷内热", "聪慧", "有担当", "神秘"],
    "abilities": ["暗器", "轻功", "天机秘术"],
    "story_summary": "天机阁圣女，掌握着一个足以颠覆武林的秘密，被暗影楼追杀中。",
    "first_appear": "第一章"
  },
  {
    "name": "暗影楼主",
    "aliases": ["楼主"],
    "basic_info": {"年龄": "未知", "性别": "未知", "身份": "暗影楼首领"},
    "personality": ["神秘", "狠辣", "野心勃勃"],
    "abilities": ["暗影秘术", "杀手组织"],
    "story_summary": "神秘反派，追杀苏瑶，企图夺取天机阁的秘密。",
    "first_appear": "第二章"
  }
]
```'''
        elif "情节" in prompt:
            return '''```json
[
  {
    "title": "命运的开端",
    "chapter": "第一章",
    "summary": "李云在村后禁地发现被追杀的神秘女子苏瑶，命运齿轮开始转动。",
    "characters": ["李云", "苏瑶"],
    "emotion": "紧张",
    "importance": 9,
    "content_ref": "那一天的夕阳，李云永远不会忘记..."
  },
  {
    "title": "逃亡之路",
    "chapter": "第二章",
    "summary": "苏瑶告知李云自己的身份和追杀者，两人连夜离开村子。",
    "characters": ["李云", "苏瑶", "暗影楼杀手"],
    "emotion": "紧张",
    "importance": 8,
    "content_ref": "苏瑶的真实身份，远比李云想象的要复杂得多..."
  }
]
```'''
        elif "关系" in prompt:
            return '''```json
[
  {"source_id": "李云", "target_id": "苏瑶", "relation_type": "师徒", "description": "苏瑶教导李云武艺", "strength": 8},
  {"source_id": "李云", "target_id": "暗影楼主", "relation_type": "敌人", "description": "暗影楼追杀苏瑶", "strength": 9}
]
```'''
        elif "灵感" in prompt or "建议" in prompt:
            return """
## 写作灵感建议

### 1. 情节发展建议
- 可以在李云与苏瑶的互动中增加更多情感层次
- 暗影楼的威胁可以更加具体化

### 2. 冲突设计
- 内在冲突：李云对未知世界的恐惧与对冒险的渴望
- 外在冲突：暗影楼的持续追杀

### 3. 伏笔建议
- 李云的剑心通明天赋来源可以是一个伏笔
"""
        else:
            return "这是一个模拟响应。请检查API配置。"


# 全局单例
def get_ai_client() -> AIAgentClient:
    """获取 AI 客户端单例"""
    return AIAgentClient()


# 向后兼容别名
ClaudeAgentClient = AIAgentClient
