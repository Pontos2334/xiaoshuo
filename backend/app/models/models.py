from sqlalchemy import Column, String, Integer, Float, Text, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.models.database import Base
import uuid


def _utcnow():
    return datetime.now(timezone.utc)


def generate_uuid():
    return str(uuid.uuid4())


class Novel(Base):
    """小说模型"""
    __tablename__ = "novels"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    path = Column(String, nullable=False)
    content_path = Column(String)
    outline_path = Column(String)
    chapter_count = Column(Integer, default=0)
    word_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    # 分析进度
    last_analyzed_chapter = Column(Integer, default=0)  # 已分析到第几章
    last_analyzed_at = Column(DateTime)  # 上次分析时间
    analysis_version = Column(Integer, default=0)  # 分析版本号

    # 关系
    characters = relationship("Character", back_populates="novel", cascade="all, delete-orphan")
    plot_nodes = relationship("PlotNode", back_populates="novel", cascade="all, delete-orphan")
    chapters = relationship("Chapter", back_populates="novel", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="novel", cascade="all, delete-orphan")
    analysis_tasks = relationship("AnalysisTask", back_populates="novel", cascade="all, delete-orphan")
    world_entities = relationship("WorldEntity", back_populates="novel", cascade="all, delete-orphan")
    foreshadows = relationship("Foreshadow", back_populates="novel", cascade="all, delete-orphan")
    arc_points = relationship("CharacterArcPoint", back_populates="novel", cascade="all, delete-orphan")
    tension_points = relationship("TensionPoint", back_populates="novel", cascade="all, delete-orphan")
    outline_nodes = relationship("OutlineNode", back_populates="novel", cascade="all, delete-orphan")


class Character(Base):
    """人物模型"""
    __tablename__ = "characters"

    id = Column(String, primary_key=True, default=generate_uuid)
    novel_id = Column(String, ForeignKey("novels.id"), nullable=False)
    name = Column(String, nullable=False)
    aliases = Column(JSON, default=list)  # 别名列表
    basic_info = Column(JSON, default=dict)  # 基本信息
    personality = Column(JSON, default=list)  # 性格特点
    abilities = Column(JSON, default=list)  # 能力
    story_summary = Column(Text)  # 故事简介
    first_appear = Column(String)  # 首次出现章节

    # 数据来源追踪
    source = Column(String, default='ai')  # 'ai' | 'user' | 'ai_modified'
    ai_version = Column(Integer, default=1)  # AI分析版本号

    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    # 关系
    novel = relationship("Novel", back_populates="characters")
    arc_points = relationship("CharacterArcPoint", back_populates="character", cascade="all, delete-orphan")
    source_relations = relationship(
        "CharacterRelation",
        foreign_keys="CharacterRelation.source_id",
        back_populates="source_character",
        cascade="all, delete-orphan"
    )
    target_relations = relationship(
        "CharacterRelation",
        foreign_keys="CharacterRelation.target_id",
        back_populates="target_character",
        cascade="all, delete-orphan"
    )


class CharacterRelation(Base):
    """人物关系模型"""
    __tablename__ = "character_relations"

    id = Column(String, primary_key=True, default=generate_uuid)
    novel_id = Column(String, ForeignKey("novels.id"), nullable=False)
    source_id = Column(String, ForeignKey("characters.id"), nullable=False)
    target_id = Column(String, ForeignKey("characters.id"), nullable=False)
    relation_type = Column(String, nullable=False)  # 关系类型
    description = Column(Text)  # 关系描述
    strength = Column(Integer, default=5)  # 关系强度 1-10

    # 关系
    source_character = relationship(
        "Character",
        foreign_keys=[source_id],
        back_populates="source_relations"
    )
    target_character = relationship(
        "Character",
        foreign_keys=[target_id],
        back_populates="target_relations"
    )


class PlotNode(Base):
    """情节节点模型"""
    __tablename__ = "plot_nodes"

    id = Column(String, primary_key=True, default=generate_uuid)
    novel_id = Column(String, ForeignKey("novels.id"), nullable=False)
    title = Column(String, nullable=False)
    chapter = Column(String)  # 所属章节
    summary = Column(Text)  # 情节概述
    characters = Column(JSON, default=list)  # 涉及人物ID
    emotion = Column(String)  # 主要情绪
    importance = Column(Integer, default=5)  # 重要程度 1-10
    content_ref = Column(Text)  # 原文引用

    # 数据来源追踪
    source = Column(String, default='ai')  # 'ai' | 'user' | 'ai_modified'
    ai_version = Column(Integer, default=1)  # AI分析版本号

    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    # 关系
    novel = relationship("Novel", back_populates="plot_nodes")
    source_connections = relationship(
        "PlotConnection",
        foreign_keys="PlotConnection.source_id",
        back_populates="source_plot",
        cascade="all, delete-orphan"
    )
    target_connections = relationship(
        "PlotConnection",
        foreign_keys="PlotConnection.target_id",
        back_populates="target_plot",
        cascade="all, delete-orphan"
    )


class PlotConnection(Base):
    """情节连接模型"""
    __tablename__ = "plot_connections"

    id = Column(String, primary_key=True, default=generate_uuid)
    novel_id = Column(String, ForeignKey("novels.id"), nullable=False)
    source_id = Column(String, ForeignKey("plot_nodes.id"), nullable=False)
    target_id = Column(String, ForeignKey("plot_nodes.id"), nullable=False)
    connection_type = Column(String, nullable=False)  # cause, parallel, foreshadow, flashback, next
    description = Column(Text)  # 连接描述

    # 关系
    source_plot = relationship(
        "PlotNode",
        foreign_keys=[source_id],
        back_populates="source_connections"
    )
    target_plot = relationship(
        "PlotNode",
        foreign_keys=[target_id],
        back_populates="target_connections"
    )


class Inspiration(Base):
    """灵感记录模型"""
    __tablename__ = "inspirations"

    id = Column(String, primary_key=True, default=generate_uuid)
    novel_id = Column(String, ForeignKey("novels.id"), nullable=True)
    type = Column(String, nullable=False)  # plot, continue, character, emotion
    target_id = Column(String)  # 关联的情节/人物ID
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=_utcnow)


class Chapter(Base):
    """章节模型"""
    __tablename__ = "chapters"

    id = Column(String, primary_key=True, default=generate_uuid)
    novel_id = Column(String, ForeignKey("novels.id"), nullable=False)
    chapter_number = Column(Integer, nullable=False)
    title = Column(String)
    content = Column(Text)
    word_count = Column(Integer, default=0)
    status = Column(String, default="draft")  # draft / completed / revised
    summary = Column(Text)  # AI生成的章节摘要

    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    # 关系
    novel = relationship("Novel", back_populates="chapters")


class ChatSession(Base):
    """对话会话模型 - 持久化人物对话历史"""
    __tablename__ = "chat_sessions"

    id = Column(String, primary_key=True)  # UUID
    novel_id = Column(String, ForeignKey("novels.id"), nullable=False)
    character_id = Column(String, ForeignKey("characters.id"), nullable=False)
    character_name = Column(String)  # 冗余存储，方便查询
    messages = Column(Text, default="[]")  # JSON array
    created_at = Column(DateTime, default=_utcnow)
    last_active = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    # 关系
    novel = relationship("Novel", back_populates="chat_sessions")


class AnalysisTask(Base):
    """分析任务模型 - 持久化异步分析任务状态"""
    __tablename__ = "analysis_tasks"

    id = Column(String, primary_key=True)  # UUID
    novel_id = Column(String, ForeignKey("novels.id"), nullable=False)
    type = Column(String, nullable=False)  # character / plot / graph
    status = Column(String, default="started")  # started / in_progress / completed / failed / cancelled
    progress = Column(Float, default=0)
    result = Column(Text)  # JSON
    error = Column(Text)
    created_at = Column(DateTime, default=_utcnow)

    # 关系
    novel = relationship("Novel", back_populates="analysis_tasks")


class WorldEntity(Base):
    """世界观实体模型"""
    __tablename__ = "world_entities"

    id = Column(String, primary_key=True, default=generate_uuid)
    novel_id = Column(String, ForeignKey("novels.id"), nullable=False)
    name = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)  # location / item / organization / event / concept / terminology
    description = Column(Text)
    attributes = Column(JSON, default=dict)  # 自定义属性键值对
    rules = Column(Text)  # 规则/约束
    source = Column(String, default="ai")  # ai / manual

    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    # 关系
    novel = relationship("Novel", back_populates="world_entities")
    source_relations = relationship(
        "EntityRelation",
        foreign_keys="EntityRelation.source_id",
        back_populates="source_entity",
        cascade="all, delete-orphan"
    )
    target_relations = relationship(
        "EntityRelation",
        foreign_keys="EntityRelation.target_id",
        back_populates="target_entity",
        cascade="all, delete-orphan"
    )


class EntityRelation(Base):
    """世界观实体关系模型"""
    __tablename__ = "entity_relations"

    id = Column(String, primary_key=True, default=generate_uuid)
    novel_id = Column(String, ForeignKey("novels.id"), nullable=False)
    source_id = Column(String, ForeignKey("world_entities.id"), nullable=False)
    target_id = Column(String, ForeignKey("world_entities.id"), nullable=False)
    relation_type = Column(String, nullable=False)
    description = Column(Text)

    # 关系
    source_entity = relationship(
        "WorldEntity",
        foreign_keys=[source_id],
        back_populates="source_relations"
    )
    target_entity = relationship(
        "WorldEntity",
        foreign_keys=[target_id],
        back_populates="target_relations"
    )


class Foreshadow(Base):
    """伏笔追踪模型"""
    __tablename__ = "foreshadows"

    id = Column(String, primary_key=True, default=generate_uuid)
    novel_id = Column(String, ForeignKey("novels.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    plant_chapter = Column(Integer, nullable=False)
    plant_description = Column(Text)
    status = Column(String, default="planted")  # planted / partially_revealed / resolved / abandoned
    resolve_chapter = Column(Integer, nullable=True)
    resolve_description = Column(Text, nullable=True)
    related_characters = Column(JSON, default=list)
    related_plots = Column(JSON, default=list)
    importance = Column(Integer, default=5)  # 1-10
    source = Column(String, default="ai")  # ai / user

    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    novel = relationship("Novel", back_populates="foreshadows")


class CharacterArcPoint(Base):
    """角色成长弧线模型"""
    __tablename__ = "character_arc_points"

    id = Column(String, primary_key=True, default=generate_uuid)
    character_id = Column(String, ForeignKey("characters.id"), nullable=False)
    novel_id = Column(String, ForeignKey("novels.id"), nullable=False)
    chapter_number = Column(Integer, nullable=False)
    psychological_state = Column(String)  # 心理状态
    emotional_state = Column(String)  # 情感状态
    ability_description = Column(String)  # 能力描述
    ability_level = Column(Integer, nullable=True)  # 能力等级 1-10
    relationship_changes = Column(JSON, default=list)  # [{target_id, change}]
    key_events = Column(JSON, default=list)  # [string]
    growth_notes = Column(Text)
    source = Column(String, default="ai")

    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    character = relationship("Character", back_populates="arc_points")
    novel = relationship("Novel", back_populates="arc_points")


class TensionPoint(Base):
    """节奏张力点模型"""
    __tablename__ = "tension_points"

    id = Column(String, primary_key=True, default=generate_uuid)
    novel_id = Column(String, ForeignKey("novels.id"), nullable=False)
    chapter_number = Column(Integer, nullable=False)
    tension_level = Column(Integer, default=5)  # 1-10
    emotion_tags = Column(JSON, default=list)  # [string]
    key_events_summary = Column(Text)
    pacing_note = Column(Text)
    reader_hook_score = Column(Integer, nullable=True)  # 1-10 前3章
    cliffhanger_score = Column(Integer, nullable=True)  # 1-10
    source = Column(String, default="ai")

    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    novel = relationship("Novel", back_populates="tension_points")


class OutlineNode(Base):
    """大纲节点模型（自引用树形结构）"""
    __tablename__ = "outline_nodes"

    id = Column(String, primary_key=True, default=generate_uuid)
    novel_id = Column(String, ForeignKey("novels.id"), nullable=False)
    parent_id = Column(String, ForeignKey("outline_nodes.id"), nullable=True)
    level = Column(Integer, nullable=False)  # 0=总纲, 1=卷, 2=章节
    title = Column(String, nullable=False)
    content = Column(Text)
    chapter_range = Column(String, nullable=True)  # "第1-10章"
    status = Column(String, default="draft")  # draft / completed / active
    sort_order = Column(Integer, default=0)
    ai_context = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    novel = relationship("Novel", back_populates="outline_nodes")
    children = relationship("OutlineNode", back_populates="parent", cascade="all, delete-orphan")
    parent = relationship("OutlineNode", back_populates="children", remote_side=[id])
