from sqlalchemy import Column, String, Integer, Text, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.database import Base
import uuid


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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    characters = relationship("Character", back_populates="novel", cascade="all, delete-orphan")
    plot_nodes = relationship("PlotNode", back_populates="novel", cascade="all, delete-orphan")


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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    novel = relationship("Novel", back_populates="characters")
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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
    created_at = Column(DateTime, default=datetime.utcnow)
