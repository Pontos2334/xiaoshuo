"""
图谱构建 API

提供知识图谱构建和管理功能
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import logging

from ..services.graph_rag.novel_graph_builder import NovelGraphBuilder
from ..services.graph_rag.novel_ontology_generator import NovelOntologyGenerator, DEFAULT_NOVEL_ONTOLOGY

router = APIRouter(tags=["graph"])
logger = logging.getLogger(__name__)


class BuildGraphRequest(BaseModel):
    """构建图谱请求"""
    novel_id: str
    text: str
    ontology: Optional[Dict[str, Any]] = None
    enable_vector_index: bool = True


class BuildGraphResponse(BaseModel):
    """构建图谱响应"""
    success: bool
    entity_count: int
    relation_count: int
    entities: List[Dict[str, Any]]
    relations: List[Dict[str, Any]]


class GraphSummaryResponse(BaseModel):
    """图谱摘要响应"""
    success: bool
    summary: Dict[str, Any]


class OntologyResponse(BaseModel):
    """本体响应"""
    success: bool
    ontology: Dict[str, Any]


@router.post("/build", response_model=BuildGraphResponse)
async def build_graph(request: BuildGraphRequest):
    """
    构建知识图谱

    从小说文本中抽取实体和关系，构建知识图谱
    """
    try:
        # 如果没有提供文本，从数据库自动读取
        if not request.text:
            from ..models.database import SessionLocal
            from ..models.models import Novel
            from ..core.file_utils import safe_read_file
            db = SessionLocal()
            try:
                novel = db.query(Novel).filter(Novel.id == request.novel_id).first()
                if novel and novel.content_path:
                    request.text = safe_read_file(novel.content_path)
            finally:
                db.close()
        if not request.text:
            raise HTTPException(status_code=400, detail="需要提供文本或有效的小说ID")

        builder = NovelGraphBuilder()
        result = builder.build(
            novel_id=request.novel_id,
            text=request.text,
            ontology=request.ontology,
            enable_vector_index=request.enable_vector_index
        )

        return BuildGraphResponse(
            success=True,
            entity_count=len(result.entities),
            relation_count=len(result.relations),
            entities=[e.to_dict() for e in result.entities],
            relations=[r.to_dict() for r in result.relations]
        )
    except Exception as e:
        logger.error(f"构建图谱失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary/{novel_id}", response_model=GraphSummaryResponse)
async def get_graph_summary(novel_id: str):
    """
    获取图谱摘要

    返回指定小说的知识图谱统计信息
    """
    try:
        builder = NovelGraphBuilder()
        summary = builder.get_graph_summary(novel_id)

        return GraphSummaryResponse(
            success=True,
            summary=summary
        )
    except Exception as e:
        logger.error(f"获取图谱摘要失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ontology", response_model=OntologyResponse)
async def get_default_ontology():
    """
    获取默认小说本体

    返回预定义的小说本体定义
    """
    try:
        return OntologyResponse(
            success=True,
            ontology=DEFAULT_NOVEL_ONTOLOGY.to_dict()
        )
    except Exception as e:
        logger.error(f"获取默认本体失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ontology/generate", response_model=OntologyResponse)
async def generate_ontology(text_sample: str):
    """
    生成本体定义

    从小说文本样本中分析生成本体定义
    """
    try:
        generator = NovelOntologyGenerator()
        ontology = generator.generate(text_sample)

        return OntologyResponse(
            success=True,
            ontology=ontology.to_dict()
        )
    except Exception as e:
        logger.error(f"生成本体失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
