"""
语义搜索 API

提供小说内容的语义搜索功能
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from ..services.vector.qdrant_service import get_qdrant_service

router = APIRouter(tags=["search"])


class SemanticSearchRequest(BaseModel):
    """语义搜索请求"""
    novel_id: str
    query: str
    limit: int = 10
    item_type: Optional[str] = None  # character, plot, text, None=全部


class SearchResponse(BaseModel):
    """搜索响应"""
    success: bool
    results: List[Dict[str, Any]]
    total: int


@router.post("/semantic", response_model=SearchResponse)
async def semantic_search(request: SemanticSearchRequest):
    """
    语义搜索

    在小说内容中进行语义搜索，支持过滤类型
    """
    try:
        qdrant = get_qdrant_service()
        results = qdrant.search(
            novel_id=request.novel_id,
            query=request.query,
            limit=request.limit,
            item_type=request.item_type
        )

        return SearchResponse(
            success=True,
            results=results,
            total=len(results)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/characters", response_model=SearchResponse)
async def search_characters(request: SemanticSearchRequest):
    """
    搜索相似人物

    根据描述搜索相似的人物
    """
    try:
        qdrant = get_qdrant_service()
        results = qdrant.search_characters(
            novel_id=request.novel_id,
            query=request.query,
            limit=request.limit
        )

        return SearchResponse(
            success=True,
            results=results,
            total=len(results)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plots", response_model=SearchResponse)
async def search_plots(request: SemanticSearchRequest):
    """
    搜索相似情节

    根据描述搜索相似的情节
    """
    try:
        qdrant = get_qdrant_service()
        results = qdrant.search_plots(
            novel_id=request.novel_id,
            query=request.query,
            limit=request.limit
        )

        return SearchResponse(
            success=True,
            results=results,
            total=len(results)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
