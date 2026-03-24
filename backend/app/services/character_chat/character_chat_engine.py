"""
人物对话引擎

处理用户与小说人物的对话交互
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from anthropic import Anthropic

from .character_profile_generator import CharacterProfile, CharacterProfileGenerator

logger = logging.getLogger(__name__)


class ChatSession:
    """对话会话"""

    def __init__(self, session_id: str, profile: CharacterProfile):
        self.session_id = session_id
        self.profile = profile
        self.messages: List[Dict[str, str]] = []
        self.created_at = datetime.now()
        self.last_active = datetime.now()

    def add_message(self, role: str, content: str):
        """添加消息"""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        self.last_active = datetime.now()

    def get_context(self, max_messages: int = 10) -> List[Dict[str, str]]:
        """获取对话上下文"""
        # 返回最近的消息
        recent = self.messages[-max_messages:] if len(self.messages) > max_messages else self.messages
        return [{"role": m["role"], "content": m["content"]} for m in recent]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "character_id": self.profile.character_id,
            "character_name": self.profile.name,
            "message_count": len(self.messages),
            "created_at": self.created_at.isoformat(),
            "last_active": self.last_active.isoformat()
        }


class CharacterChatEngine:
    """
    人物对话引擎

    管理用户与小说人物的对话交互
    """

    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        self.base_url = base_url or os.getenv('ANTHROPIC_BASE_URL')
        self.model = model or os.getenv('CLAUDE_MODEL', 'glm-5')

        if self.api_key:
            self.client = Anthropic(
                api_key=self.api_key,
                base_url=self.base_url
            )
            logger.info(f"CharacterChatEngine 初始化完成: model={self.model}")
        else:
            self.client = None
            logger.warning("未配置 API Key，对话将返回固定响应")

        # 会话管理
        self.sessions: Dict[str, ChatSession] = {}

        # 档案缓存
        self.profiles: Dict[str, CharacterProfile] = {}

    def create_session(
        self,
        character_id: str,
        character_data: Dict[str, Any],
        novel_context: str = "",
        relations: List[Dict[str, Any]] = None
    ) -> ChatSession:
        """
        创建对话会话

        Args:
            character_id: 人物ID
            character_data: 人物数据
            novel_context: 小说上下文
            relations: 人物关系

        Returns:
            对话会话
        """
        import uuid

        session_id = str(uuid.uuid4())

        # 生成或获取人物档案
        if character_id in self.profiles:
            profile = self.profiles[character_id]
        else:
            generator = CharacterProfileGenerator(
                api_key=self.api_key,
                base_url=self.base_url,
                model=self.model
            )
            profile = generator.generate(
                character_id=character_id,
                character_data=character_data,
                novel_context=novel_context,
                relations=relations
            )
            self.profiles[character_id] = profile

        session = ChatSession(session_id, profile)
        self.sessions[session_id] = session

        logger.info(f"创建对话会话: session_id={session_id}, character={profile.name}")

        return session

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """获取会话"""
        return self.sessions.get(session_id)

    def chat(
        self,
        session_id: str,
        user_message: str,
        context: str = ""
    ) -> Dict[str, Any]:
        """
        发送消息并获取回复

        Args:
            session_id: 会话ID
            user_message: 用户消息
            context: 额外上下文

        Returns:
            响应数据
        """
        session = self.sessions.get(session_id)
        if not session:
            return {
                "success": False,
                "error": "会话不存在"
            }

        # 添加用户消息
        session.add_message("user", user_message)

        if not self.client:
            # 无 API 时返回固定响应
            response_text = f"（{session.profile.name}沉默了一会儿）我是{session.profile.name}。你有什么事吗？"
            session.add_message("assistant", response_text)
            return {
                "success": True,
                "response": response_text,
                "emotion": "neutral"
            }

        # 构建消息列表
        system_prompt = session.profile.get_system_prompt()

        messages = []

        # 添加历史对话
        history = session.get_context(max_messages=10)
        messages.extend(history)

        # 添加额外上下文
        if context:
            messages.insert(0, {
                "role": "user",
                "content": f"[背景信息]\n{context}"
            })

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                system=system_prompt,
                messages=messages
            )

            response_text = response.content[0].text

            # 添加助手回复
            session.add_message("assistant", response_text)

            # 分析情绪（简单关键词检测）
            emotion = self._detect_emotion(response_text)

            return {
                "success": True,
                "response": response_text,
                "emotion": emotion
            }

        except Exception as e:
            logger.error(f"对话失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _detect_emotion(self, text: str) -> str:
        """简单情绪检测"""
        emotion_keywords = {
            "happy": ["哈哈", "开心", "高兴", "笑了", "好极了"],
            "sad": ["唉", "难过", "伤心", "眼泪", "遗憾"],
            "angry": ["哼", "可恶", "混蛋", "气死", "愤怒"],
            "surprised": ["啊", "什么", "竟然", "没想到", "意外"],
            "fear": ["害怕", "恐惧", "危险", "小心"],
            "neutral": []
        }

        for emotion, keywords in emotion_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    return emotion

        return "neutral"

    def get_chat_history(self, session_id: str) -> List[Dict[str, Any]]:
        """获取对话历史"""
        session = self.sessions.get(session_id)
        if not session:
            return []

        return session.messages

    def close_session(self, session_id: str) -> bool:
        """关闭会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"关闭会话: session_id={session_id}")
            return True
        return False

    def list_sessions(self) -> List[Dict[str, Any]]:
        """列出所有会话"""
        return [session.to_dict() for session in self.sessions.values()]


# 单例实例
_chat_engine: Optional[CharacterChatEngine] = None


def get_chat_engine() -> CharacterChatEngine:
    """获取对话引擎单例"""
    global _chat_engine
    if _chat_engine is None:
        _chat_engine = CharacterChatEngine()
    return _chat_engine
