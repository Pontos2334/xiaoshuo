"""
人物对话 API

提供与小说人物对话的功能
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import logging

from ..services.character_chat.character_chat_engine import get_chat_engine
from ..services.character_chat.character_profile_generator import CharacterProfileGenerator

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)


class CreateSessionRequest(BaseModel):
    """创建会话请求"""
    character_id: str
    character_data: Dict[str, Any]
    novel_context: str = ""
    relations: Optional[List[Dict[str, Any]]] = None


class ChatRequest(BaseModel):
    """对话请求"""
    session_id: str
    message: str
    context: str = ""


class ChatResponse(BaseModel):
    """对话响应"""
    success: bool
    response: Optional[str] = None
    emotion: Optional[str] = None
    error: Optional[str] = None


class SessionResponse(BaseModel):
    """会话响应"""
    success: bool
    session_id: Optional[str] = None
    character_name: Optional[str] = None
    message_count: Optional[int] = None


class ProfileResponse(BaseModel):
    """档案响应"""
    success: bool
    profile: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@router.post("/session", response_model=SessionResponse)
async def create_session(request: CreateSessionRequest):
    """
    创建对话会话

    为指定人物创建对话会话
    """
    try:
        engine = get_chat_engine()
        session = engine.create_session(
            character_id=request.character_id,
            character_data=request.character_data,
            novel_context=request.novel_context,
            relations=request.relations
        )

        return SessionResponse(
            success=True,
            session_id=session.session_id,
            character_name=session.profile.name,
            message_count=0
        )
    except Exception as e:
        logger.error(f"创建会话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/message", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """
    发送消息

    在会话中发送消息并获取人物回复
    """
    try:
        engine = get_chat_engine()
        result = engine.chat(
            session_id=request.session_id,
            user_message=request.message,
            context=request.context
        )

        return ChatResponse(
            success=result.get("success", False),
            response=result.get("response"),
            emotion=result.get("emotion"),
            error=result.get("error")
        )
    except Exception as e:
        logger.error(f"发送消息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{session_id}")
async def get_history(session_id: str):
    """
    获取对话历史

    返回指定会话的对话历史
    """
    try:
        engine = get_chat_engine()
        history = engine.get_chat_history(session_id)

        return {
            "success": True,
            "history": history
        }
    except Exception as e:
        logger.error(f"获取历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/session/{session_id}")
async def close_session(session_id: str):
    """
    关闭会话

    关闭并清理会话资源
    """
    try:
        engine = get_chat_engine()
        success = engine.close_session(session_id)

        return {
            "success": success,
            "message": "会话已关闭" if success else "会话不存在"
        }
    except Exception as e:
        logger.error(f"关闭会话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions")
async def list_sessions():
    """
    列出所有会话

    返回当前活跃的所有会话
    """
    try:
        engine = get_chat_engine()
        sessions = engine.list_sessions()

        return {
            "success": True,
            "sessions": sessions
        }
    except Exception as e:
        logger.error(f"列出会话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/profile/generate", response_model=ProfileResponse)
async def generate_profile(
    character_id: str,
    character_data: Dict[str, Any],
    novel_context: str = "",
    relations: Optional[List[Dict[str, Any]]] = None
):
    """
    生成人物档案

    从人物数据和小说内容生成详细的人物档案
    """
    try:
        generator = CharacterProfileGenerator()
        profile = generator.generate(
            character_id=character_id,
            character_data=character_data,
            novel_context=novel_context,
            relations=relations
        )

        return ProfileResponse(
            success=True,
            profile=profile.to_dict()
        )
    except Exception as e:
        logger.error(f"生成档案失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profile/{character_id}", response_model=ProfileResponse)
async def get_profile(character_id: str):
    """
    获取人物档案

    返回缓存的人物档案
    """
    try:
        engine = get_chat_engine()

        if character_id in engine.profiles:
            profile = engine.profiles[character_id]
            return ProfileResponse(
                success=True,
                profile=profile.to_dict()
            )
        else:
            return ProfileResponse(
                success=False,
                error="人物档案不存在"
            )
    except Exception as e:
        logger.error(f"获取档案失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
