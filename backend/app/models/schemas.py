from pydantic import BaseModel, field_validator, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime
import json


def to_camel(string: str) -> str:
    """将 snake_case 转换为 camelCase"""
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


class CamelCaseModel(BaseModel):
    """自动将字段名转换为 camelCase 的基类"""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        alias_generator=to_camel,
        serialize_by_alias=True,  # 序列化时也使用别名
    )


# ========== 小说相关 ==========
class NovelBase(CamelCaseModel):
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


# ========== 人物相关 ==========
class CharacterBase(CamelCaseModel):
    name: str
    aliases: List[str] = []
    basic_info: Optional[Dict[str, Any] | str] = None
    personality: List[str] = []
    abilities: List[str] = []
    story_summary: Optional[str] = None
    first_appear: Optional[str] = None


class CharacterCreate(CharacterBase):
    novel_id: str


class CharacterUpdate(CamelCaseModel):
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
class CharacterRelationBase(CamelCaseModel):
    source_id: str
    target_id: str
    relation_type: str
    description: Optional[str] = None
    strength: int = 5


class CharacterRelationCreate(CharacterRelationBase):
    novel_id: str


class CharacterRelationUpdate(CamelCaseModel):
    relation_type: Optional[str] = None
    description: Optional[str] = None
    strength: Optional[int] = None


class CharacterRelationResponse(CharacterRelationBase):
    id: str
    novel_id: str


# ========== 情节相关 ==========
class PlotNodeBase(CamelCaseModel):
    title: str
    chapter: Optional[str] = None
    summary: Optional[str] = None
    characters: List[str] = []
    emotion: Optional[str] = None
    importance: int = 5
    content_ref: Optional[str] = None


class PlotNodeCreate(PlotNodeBase):
    novel_id: str


class PlotNodeUpdate(CamelCaseModel):
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


# ========== 情节连接相关 ==========
class PlotConnectionBase(CamelCaseModel):
    source_id: str
    target_id: str
    connection_type: str  # cause, parallel, foreshadow, flashback, next
    description: Optional[str] = None


class PlotConnectionCreate(PlotConnectionBase):
    novel_id: str


class PlotConnectionUpdate(CamelCaseModel):
    connection_type: Optional[str] = None
    description: Optional[str] = None


class PlotConnectionResponse(PlotConnectionBase):
    id: str
    novel_id: str


# ========== 灵感相关 ==========
class InspirationRequest(CamelCaseModel):
    novel_id: Optional[str] = None
    type: str  # scene, plot, continue, character, emotion
    target_id: Optional[str] = None  # 兼容单个ID
    target_ids: Optional[List[str]] = None  # 支持多个ID
    context: Optional[str] = None


class InspirationResponse(CamelCaseModel):
    id: str
    type: str
    target_id: Optional[str]
    content: str
    created_at: datetime


# ========== 通用响应 ==========
class ApiResponse(CamelCaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None


# ========== 章节相关 ==========
class ChapterBase(CamelCaseModel):
    chapter_number: int
    title: Optional[str] = None
    word_count: int = 0
    status: str = "draft"  # draft / completed / revised


class ChapterResponse(ChapterBase):
    id: str
    novel_id: str
    summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ChapterDetailResponse(ChapterResponse):
    content: Optional[str] = None


class ChapterUpdate(CamelCaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    status: Optional[str] = None


class ChapterReorder(CamelCaseModel):
    novel_id: str
    chapter_ids: List[str]


# ========== 对话会话相关 ==========
class ChatSessionResponse(CamelCaseModel):
    id: str
    novel_id: str
    character_id: str
    character_name: Optional[str] = None
    message_count: int = 0
    created_at: datetime
    last_active: datetime


# ========== 分析任务相关 ==========
class AnalysisTaskResponse(CamelCaseModel):
    id: str
    novel_id: str
    type: str
    status: str
    progress: float = 0
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: datetime

    @field_validator('result', mode='before')
    @classmethod
    def parse_result(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return v
        return v


# ========== 世界观实体相关 ==========
class WorldEntityBase(CamelCaseModel):
    name: str
    entity_type: str  # location / item / organization / event / concept / terminology
    description: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None
    rules: Optional[str] = None


class WorldEntityCreate(WorldEntityBase):
    novel_id: str
    source: str = "manual"


class WorldEntityUpdate(CamelCaseModel):
    name: Optional[str] = None
    entity_type: Optional[str] = None
    description: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None
    rules: Optional[str] = None


class WorldEntityResponse(WorldEntityBase):
    id: str
    novel_id: str
    source: str
    created_at: datetime
    updated_at: datetime

    @field_validator('attributes', mode='before')
    @classmethod
    def parse_attributes(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return {}
        return v if v else {}


# ========== 实体关系相关 ==========
class EntityRelationBase(CamelCaseModel):
    source_id: str
    target_id: str
    relation_type: str
    description: Optional[str] = None


class EntityRelationCreate(EntityRelationBase):
    novel_id: str


class EntityRelationUpdate(CamelCaseModel):
    relation_type: Optional[str] = None
    description: Optional[str] = None


class EntityRelationResponse(EntityRelationBase):
    id: str
    novel_id: str
    source_name: Optional[str] = None
    target_name: Optional[str] = None


# ========== 一致性检查相关 ==========
class ConsistencyIssue(CamelCaseModel):
    type: str  # character / timeline / rule / relation
    severity: str = "warning"  # error / warning / info
    description: str
    chapter_a: Optional[str] = None
    chapter_b: Optional[str] = None
    detail: Optional[str] = None
    suggestion: Optional[str] = None


class ConsistencyCheckResponse(CamelCaseModel):
    novel_id: str
    total_issues: int
    issues: List[ConsistencyIssue]


# ========== 伏笔追踪相关 ==========
class ForeshadowBase(CamelCaseModel):
    title: str
    description: Optional[str] = None
    plant_chapter: int
    plant_description: Optional[str] = None
    status: str = "planted"
    resolve_chapter: Optional[int] = None
    resolve_description: Optional[str] = None
    related_characters: List[str] = []
    related_plots: List[str] = []
    importance: int = 5
    source: str = "ai"


class ForeshadowCreate(ForeshadowBase):
    novel_id: str


class ForeshadowUpdate(CamelCaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    plant_chapter: Optional[int] = None
    plant_description: Optional[str] = None
    status: Optional[str] = None
    resolve_chapter: Optional[int] = None
    resolve_description: Optional[str] = None
    related_characters: Optional[List[str]] = None
    related_plots: Optional[List[str]] = None
    importance: Optional[int] = None


class ForeshadowResponse(ForeshadowBase):
    id: str
    novel_id: str
    created_at: datetime
    updated_at: datetime

    @field_validator('related_characters', 'related_plots', mode='before')
    @classmethod
    def parse_list_fields(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return []
        return v if v else []


# ========== 角色成长弧线相关 ==========
class CharacterArcPointBase(CamelCaseModel):
    chapter_number: int
    psychological_state: Optional[str] = None
    emotional_state: Optional[str] = None
    ability_description: Optional[str] = None
    ability_level: Optional[int] = None
    relationship_changes: List[Dict[str, Any]] = []
    key_events: List[str] = []
    growth_notes: Optional[str] = None
    source: str = "ai"


class CharacterArcPointCreate(CharacterArcPointBase):
    character_id: str
    novel_id: str


class CharacterArcPointUpdate(CamelCaseModel):
    psychological_state: Optional[str] = None
    emotional_state: Optional[str] = None
    ability_description: Optional[str] = None
    ability_level: Optional[int] = None
    relationship_changes: Optional[List[Dict[str, Any]]] = None
    key_events: Optional[List[str]] = None
    growth_notes: Optional[str] = None


class CharacterArcPointResponse(CharacterArcPointBase):
    id: str
    character_id: str
    novel_id: str
    created_at: datetime
    updated_at: datetime

    @field_validator('relationship_changes', 'key_events', mode='before')
    @classmethod
    def parse_json_list(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return []
        return v if v else []


# ========== 节奏张力相关 ==========
class TensionPointBase(CamelCaseModel):
    chapter_number: int
    tension_level: int = 5
    emotion_tags: List[str] = []
    key_events_summary: Optional[str] = None
    pacing_note: Optional[str] = None
    reader_hook_score: Optional[int] = None
    cliffhanger_score: Optional[int] = None
    source: str = "ai"


class TensionPointCreate(TensionPointBase):
    novel_id: str


class TensionPointUpdate(CamelCaseModel):
    tension_level: Optional[int] = None
    emotion_tags: Optional[List[str]] = None
    key_events_summary: Optional[str] = None
    pacing_note: Optional[str] = None
    reader_hook_score: Optional[int] = None
    cliffhanger_score: Optional[int] = None


class TensionPointResponse(TensionPointBase):
    id: str
    novel_id: str
    created_at: datetime
    updated_at: datetime

    @field_validator('emotion_tags', mode='before')
    @classmethod
    def parse_list_fields(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return []
        return v if v else []


# ========== 大纲节点相关 ==========
class OutlineNodeBase(CamelCaseModel):
    level: int  # 0=总纲, 1=卷, 2=章节
    title: str
    content: Optional[str] = None
    chapter_range: Optional[str] = None
    status: str = "draft"
    sort_order: int = 0


class OutlineNodeCreate(OutlineNodeBase):
    novel_id: str
    parent_id: Optional[str] = None
    ai_context: Optional[Dict[str, Any]] = None


class OutlineNodeUpdate(CamelCaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    chapter_range: Optional[str] = None
    status: Optional[str] = None
    sort_order: Optional[int] = None
    ai_context: Optional[Dict[str, Any]] = None


class OutlineNodeResponse(OutlineNodeBase):
    id: str
    novel_id: str
    parent_id: Optional[str] = None
    ai_context: Optional[Dict[str, Any]] = None
    children: List['OutlineNodeResponse'] = []
    created_at: datetime
    updated_at: datetime

    @field_validator('ai_context', mode='before')
    @classmethod
    def parse_ai_context(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return None
        return v


# ========== 深度一致性检查相关 ==========
class DeepConsistencyIssue(CamelCaseModel):
    type: str  # character / timeline / power_system / geography / naming
    severity: str = "warning"  # error / warning / info
    description: str
    chapter_a: Optional[str] = None
    chapter_b: Optional[str] = None
    detail: Optional[str] = None
    suggestion: Optional[str] = None


class DeepConsistencyCheckResponse(CamelCaseModel):
    novel_id: str
    total_issues: int
    checks_run: List[str]
    issues: List[DeepConsistencyIssue]
