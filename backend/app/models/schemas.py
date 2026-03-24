from pydantic import BaseModel, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime
import json


# ========== 小说相关 ==========
class NovelBase(BaseModel):
    name: str
    path: str
    content_path: Optional[str] = None
    outline_path: Optional[str] = None


class NovelCreate(NovelBase):
    pass


class NovelResponse(NovelBase):
    id: str
    chapter_count: int
    word_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ========== 人物相关 ==========
class CharacterBase(BaseModel):
    name: str
    aliases: List[str] = []
    basic_info: Optional[Dict[str, Any] | str] = None
    personality: List[str] = []
    abilities: List[str] = []
    story_summary: Optional[str] = None
    first_appear: Optional[str] = None


class CharacterCreate(CharacterBase):
    novel_id: str


class CharacterUpdate(BaseModel):
    name: Optional[str] = None
    aliases: Optional[List[str]] = None
    basic_info: Optional[Dict[str, Any]] = None
    personality: Optional[List[str]] = None
    abilities: Optional[List[str]] = None
    story_summary: Optional[str] = None
    first_appear: Optional[str] = None


class CharacterResponse(CharacterBase):
    id: str
    novel_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @field_validator('basic_info', mode='before')
    @classmethod
    def parse_basic_info(cls, v):
        """自动解析 basic_info JSON 字符串"""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return {}
        return v if v else {}

    @field_validator('aliases', 'personality', 'abilities', mode='before')
    @classmethod
    def parse_list_fields(cls, v):
        """自动解析列表字段 JSON 字符串"""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return []
        return v if v else []


# ========== 人物关系相关 ==========
class CharacterRelationBase(BaseModel):
    source_id: str
    target_id: str
    relation_type: str
    description: Optional[str] = None
    strength: int = 5


class CharacterRelationCreate(CharacterRelationBase):
    novel_id: str


class CharacterRelationUpdate(BaseModel):
    relation_type: Optional[str] = None
    description: Optional[str] = None
    strength: Optional[int] = None


class CharacterRelationResponse(CharacterRelationBase):
    id: str
    novel_id: str

    class Config:
        from_attributes = True


# ========== 情节相关 ==========
class PlotNodeBase(BaseModel):
    title: str
    chapter: Optional[str] = None
    summary: Optional[str] = None
    characters: List[str] = []
    emotion: Optional[str] = None
    importance: int = 5
    content_ref: Optional[str] = None


class PlotNodeCreate(PlotNodeBase):
    novel_id: str


class PlotNodeUpdate(BaseModel):
    title: Optional[str] = None
    chapter: Optional[str] = None
    summary: Optional[str] = None
    characters: Optional[List[str]] = None
    emotion: Optional[str] = None
    importance: Optional[int] = None
    content_ref: Optional[str] = None


class PlotNodeResponse(PlotNodeBase):
    id: str
    novel_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ========== 情节连接相关 ==========
class PlotConnectionBase(BaseModel):
    source_id: str
    target_id: str
    connection_type: str  # cause, parallel, foreshadow, flashback, next
    description: Optional[str] = None


class PlotConnectionCreate(PlotConnectionBase):
    novel_id: str


class PlotConnectionUpdate(BaseModel):
    connection_type: Optional[str] = None
    description: Optional[str] = None


class PlotConnectionResponse(PlotConnectionBase):
    id: str
    novel_id: str

    class Config:
        from_attributes = True


# ========== 灵感相关 ==========
class InspirationRequest(BaseModel):
    novel_id: Optional[str] = None
    type: str  # scene, plot, continue, character, emotion
    target_id: Optional[str] = None  # 兼容单个ID
    target_ids: Optional[List[str]] = None  # 支持多个ID
    context: Optional[str] = None


class InspirationResponse(BaseModel):
    id: str
    type: str
    target_id: Optional[str]
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


# ========== 通用响应 ==========
class ApiResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
