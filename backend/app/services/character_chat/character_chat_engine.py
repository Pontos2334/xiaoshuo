"""
人物对话引擎

处理用户与小说人物的对话交互，支持 SQLite 持久化
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from openai import OpenAI

from app.core.config import settings

from .character_profile_generator import CharacterProfile, CharacterProfileGenerator

logger = logging.getLogger(__name__)


def _get_db_session():
    """获取数据库会话"""
    from app.models.database import SessionLocal
    return SessionLocal()


def _persist_session(session: "ChatSession", novel_id: str):
    """将会话持久化到数据库"""
    try:
        from app.models.models import ChatSession as ChatSessionModel
        db = _get_db_session()
        try:
            record = db.query(ChatSessionModel).filter(
                ChatSessionModel.id == session.session_id
            ).first()
            messages_json = json.dumps(session.messages, ensure_ascii=False)

            if record:
                record.messages = messages_json
                record.last_active = datetime.utcnow()
            else:
                record = ChatSessionModel(
                    id=session.session_id,
                    novel_id=novel_id,
                    character_id=session.profile.character_id,
                    character_name=session.profile.name,
                    messages=messages_json
                )
                db.add(record)
            db.commit()
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"持久化会话失败: {e}")


def _load_session_from_db(session_id: str) -> Optional[Dict[str, Any]]:
    """从数据库加载会话"""
    try:
        from app.models.models import ChatSession as ChatSessionModel
        db = _get_db_session()
        try:
            record = db.query(ChatSessionModel).filter(
                ChatSessionModel.id == session_id
            ).first()
            if record:
                return {
                    "id": record.id,
                    "novel_id": record.novel_id,
                    "character_id": record.character_id,
                    "character_name": record.character_name,
                    "messages": json.loads(record.messages) if record.messages else [],
                    "created_at": record.created_at,
                    "last_active": record.last_active
                }
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"加载会话失败: {e}")
    return None


def _delete_session_from_db(session_id: str):
    """从数据库删除会话"""
    try:
        from app.models.models import ChatSession as ChatSessionModel
        db = _get_db_session()
        try:
            db.query(ChatSessionModel).filter(
                ChatSessionModel.id == session_id
            ).delete()
            db.commit()
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"删除会话记录失败: {e}")


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

    # 会话管理配置
    MAX_SESSIONS = 100  # 最大会话数
    SESSION_TIMEOUT_HOURS = 24  # 会话超时时间（小时）

    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.api_key = api_key or settings.DEEPSEEK_API_KEY
        self.base_url = base_url or settings.DEEPSEEK_BASE_URL
        self.model = model or settings.DEEPSEEK_MODEL

        if self.api_key:
            self.client = OpenAI(
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

    def _cleanup_expired_sessions(self) -> int:
        """
        清理过期会话

        Returns:
            清理的会话数量
        """
        now = datetime.now()
        timeout_seconds = self.SESSION_TIMEOUT_HOURS * 3600

        expired_session_ids = [
            sid for sid, session in self.sessions.items()
            if (now - session.last_active).total_seconds() > timeout_seconds
        ]

        for sid in expired_session_ids:
            del self.sessions[sid]
            # 同时清理对应的档案缓存（如果没有其他会话使用）
            profile_id = None
            for pid, profile in self.profiles.items():
                if any(s.profile.character_id == pid for s in self.sessions.values()):
                    continue
                else:
                    profile_id = pid
                    break
            if profile_id and profile_id in self.profiles:
                del self.profiles[profile_id]

        if expired_session_ids:
            logger.info(f"清理了 {len(expired_session_ids)} 个过期会话")

        return len(expired_session_ids)

    def _cleanup_oldest_sessions(self, count: int) -> int:
        """
        清理最旧的会话

        Args:
            count: 要清理的数量

        Returns:
            实际清理的数量
        """
        if not self.sessions:
            return 0

        # 按最后活跃时间排序
        sorted_sessions = sorted(
            self.sessions.items(),
            key=lambda x: x[1].last_active
        )

        cleaned = 0
        for sid, _ in sorted_sessions[:count]:
            if sid in self.sessions:
                del self.sessions[sid]
                cleaned += 1

        logger.info(f"清理了 {cleaned} 个最旧会话")
        return cleaned

    def create_session(
        self,
        character_id: str,
        character_data: Dict[str, Any],
        novel_context: str = "",
        relations: List[Dict[str, Any]] = None,
        novel_id: str = ""
    ) -> ChatSession:
        """
        创建对话会话

        Args:
            character_id: 人物ID
            character_data: 人物数据
            novel_context: 小说上下文
            relations: 人物关系
            novel_id: 小说ID（用于持久化）

        Returns:
            对话会话
        """
        import uuid

        # 检查并清理过期会话
        self._cleanup_expired_sessions()

        # 如果会话数仍然超过限制，清理最旧的
        if len(self.sessions) >= self.MAX_SESSIONS:
            excess = len(self.sessions) - self.MAX_SESSIONS + 1
            self._cleanup_oldest_sessions(excess)

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
        session._novel_id = novel_id  # 存储小说ID用于持久化
        self.sessions[session_id] = session

        # 持久化到数据库
        if novel_id:
            _persist_session(session, novel_id)

        logger.info(f"创建对话会话: session_id={session_id}, character={profile.name}")

        return session

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """获取会话（内存优先，fallback 到数据库）"""
        session = self.sessions.get(session_id)
        if session:
            return session

        # 尝试从数据库恢复
        db_data = _load_session_from_db(session_id)
        if db_data:
            # 需要重新生成 profile
            character_id = db_data.get("character_id")
            if character_id and character_id in self.profiles:
                profile = self.profiles[character_id]
                session = ChatSession(session_id, profile)
                session.messages = db_data.get("messages", [])
                session._novel_id = db_data.get("novel_id", "")
                self.sessions[session_id] = session
                return session

        return None

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
            if system_prompt:
                messages.insert(0, {"role": "system", "content": system_prompt})
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=1000,
                messages=messages
            )

            response_text = response.choices[0].message.content

            # 添加助手回复
            session.add_message("assistant", response_text)

            # 持久化到数据库
            if hasattr(session, '_novel_id') and session._novel_id:
                _persist_session(session, session._novel_id)

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
        """获取对话历史（内存优先，fallback 到数据库）"""
        session = self.sessions.get(session_id)
        if session:
            return session.messages

        # 尝试从数据库加载
        db_data = _load_session_from_db(session_id)
        if db_data:
            return db_data.get("messages", [])

        return []

    def close_session(self, session_id: str) -> bool:
        """关闭会话（同时删除数据库记录）"""
        if session_id in self.sessions:
            del self.sessions[session_id]
        _delete_session_from_db(session_id)
        logger.info(f"关闭会话: session_id={session_id}")
        return True

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
