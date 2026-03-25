from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Optional

from app.models.database import get_db
from app.models.models import Inspiration, Novel, Character, PlotNode
from app.models.schemas import InspirationRequest, InspirationResponse, ApiResponse
from app.services.inspiration_gen import InspirationGenerator
from app.core.file_utils import safe_read_file

router = APIRouter()

# 原文片段最大长度
MAX_ORIGINAL_TEXT_LENGTH = 2000


def get_targets_by_ids(db: Session, target_ids: List[str]):
    """根据 ID 列表获取人物和情节"""
    characters = []
    plot_nodes = []

    for target_id in target_ids:
        # 尝试作为人物查找
        char = db.query(Character).filter(Character.id == target_id).first()
        if char:
            characters.append(char)
            continue

        # 尝试作为情节查找
        plot = db.query(PlotNode).filter(PlotNode.id == target_id).first()
        if plot:
            plot_nodes.append(plot)

    return characters, plot_nodes


def get_original_text_context(novel_id: str, db: Session, max_length: int = MAX_ORIGINAL_TEXT_LENGTH) -> Optional[str]:
    """获取小说原文作为风格参考"""
    novel = db.query(Novel).filter(Novel.id == novel_id).first()
    if not novel or not novel.content_path:
        return None

    content = safe_read_file(novel.content_path)
    if not content:
        return None

    # 取原文的前面部分作为风格参考
    return content[:max_length]


def get_plot_original_text(plot_nodes: List[PlotNode], novel_id: str, db: Session, max_length: int = 1000) -> Optional[str]:
    """获取情节相关的原文片段"""
    if not plot_nodes:
        return get_original_text_context(novel_id, db, max_length)

    novel = db.query(Novel).filter(Novel.id == novel_id).first()
    if not novel or not novel.content_path:
        return None

    content = safe_read_file(novel.content_path)
    if not content:
        return None

    # 如果情节有原文引用，优先使用
    for plot in plot_nodes:
        if hasattr(plot, 'content_ref') and plot.content_ref:
            return plot.content_ref[:max_length]

    # 否则返回小说开头作为风格参考
    return content[:max_length]


@router.post("/scene", response_model=ApiResponse)
async def get_scene_inspiration(
    request: InspirationRequest,
    db: Session = Depends(get_db)
):
    """基于选定的人物和情节生成场景灵感"""
    # 合并 target_id 和 target_ids
    target_ids = request.target_ids or []
    if request.target_id and request.target_id not in target_ids:
        target_ids.append(request.target_id)

    characters, plot_nodes = get_targets_by_ids(db, target_ids)

    # 获取原文作为风格参考
    original_text = None
    if request.novel_id:
        original_text = get_original_text_context(request.novel_id, db)

    # 生成灵感
    generator = InspirationGenerator()
    inspiration_content = await generator.generate_scene_inspiration(
        characters=characters,
        plot_nodes=plot_nodes,
        original_text=original_text,
        context=request.context
    )

    # 保存灵感
    inspiration = Inspiration(
        novel_id=request.novel_id,
        type="scene",
        target_id=request.target_id,
        content=inspiration_content
    )
    db.add(inspiration)
    db.commit()
    db.refresh(inspiration)

    return ApiResponse(
        success=True,
        data=InspirationResponse.model_validate(inspiration).model_dump()
    )


@router.post("/plot", response_model=ApiResponse)
async def get_plot_inspiration(
    request: InspirationRequest,
    db: Session = Depends(get_db)
):
    """为指定情节生成灵感"""
    # 合并 target_id 和 target_ids
    target_ids = request.target_ids or []
    if request.target_id and request.target_id not in target_ids:
        target_ids.append(request.target_id)

    characters, plot_nodes = get_targets_by_ids(db, target_ids)

    # 如果没有指定情节，尝试获取所有情节
    if not plot_nodes and request.novel_id:
        plot_nodes = db.query(PlotNode).filter(
            PlotNode.novel_id == request.novel_id
        ).all()[:5]  # 限制数量

    # 获取原文
    original_text = None
    if request.novel_id:
        original_text = get_plot_original_text(plot_nodes, request.novel_id, db)

    # 生成灵感
    generator = InspirationGenerator()
    inspiration_content = await generator.generate_plot_inspiration(
        plot_nodes=plot_nodes,
        characters=characters,
        original_text=original_text,
        context=request.context
    )

    # 保存灵感
    inspiration = Inspiration(
        novel_id=request.novel_id,
        type="plot",
        target_id=request.target_id,
        content=inspiration_content
    )
    db.add(inspiration)
    db.commit()
    db.refresh(inspiration)

    return ApiResponse(
        success=True,
        data=InspirationResponse.model_validate(inspiration).model_dump()
    )


@router.post("/continue", response_model=ApiResponse)
async def get_continue_inspiration(
    request: InspirationRequest,
    db: Session = Depends(get_db)
):
    """生成后续情节发展建议"""
    # 合并 target_id 和 target_ids
    target_ids = request.target_ids or []
    if request.target_id and request.target_id not in target_ids:
        target_ids.append(request.target_id)

    characters, plot_nodes = get_targets_by_ids(db, target_ids)

    # 如果没有指定，获取所有人物和情节
    if request.novel_id:
        if not characters:
            characters = db.query(Character).filter(
                Character.novel_id == request.novel_id
            ).all()
        if not plot_nodes:
            plot_nodes = db.query(PlotNode).filter(
                PlotNode.novel_id == request.novel_id
            ).all()

    # 获取原文
    original_text = None
    if request.novel_id:
        original_text = get_original_text_context(request.novel_id, db)

    # 生成灵感
    generator = InspirationGenerator()
    inspiration_content = await generator.generate_continue_inspiration(
        characters=characters,
        plot_nodes=plot_nodes,
        original_text=original_text,
        context=request.context
    )

    # 保存灵感
    inspiration = Inspiration(
        novel_id=request.novel_id,
        type="continue",
        content=inspiration_content
    )
    db.add(inspiration)
    db.commit()
    db.refresh(inspiration)

    return ApiResponse(
        success=True,
        data=InspirationResponse.model_validate(inspiration).model_dump()
    )


@router.post("/character", response_model=ApiResponse)
async def get_character_inspiration(
    request: InspirationRequest,
    db: Session = Depends(get_db)
):
    """为指定角色生成发展建议"""
    # 合并 target_id 和 target_ids
    target_ids = request.target_ids or []
    if request.target_id and request.target_id not in target_ids:
        target_ids.append(request.target_id)

    characters, plot_nodes = get_targets_by_ids(db, target_ids)

    if not characters:
        raise HTTPException(status_code=400, detail="请选择至少一个角色")

    # 获取原文
    original_text = None
    if request.novel_id:
        original_text = get_original_text_context(request.novel_id, db)

    # 生成灵感
    generator = InspirationGenerator()
    inspiration_content = await generator.generate_character_inspiration(
        characters=characters,
        plot_nodes=plot_nodes,
        original_text=original_text,
        context=request.context
    )

    # 保存灵感
    inspiration = Inspiration(
        novel_id=request.novel_id,
        type="character",
        target_id=request.target_id,
        content=inspiration_content
    )
    db.add(inspiration)
    db.commit()
    db.refresh(inspiration)

    return ApiResponse(
        success=True,
        data=InspirationResponse.model_validate(inspiration).model_dump()
    )


@router.post("/emotion", response_model=ApiResponse)
async def get_emotion_inspiration(
    request: InspirationRequest,
    db: Session = Depends(get_db)
):
    """为指定情节生成情绪渲染建议"""
    # 合并 target_id 和 target_ids
    target_ids = request.target_ids or []
    if request.target_id and request.target_id not in target_ids:
        target_ids.append(request.target_id)

    characters, plot_nodes = get_targets_by_ids(db, target_ids)

    if not plot_nodes:
        raise HTTPException(status_code=400, detail="请选择至少一个情节")

    # 获取原文
    original_text = None
    if request.novel_id:
        original_text = get_plot_original_text(plot_nodes, request.novel_id, db)

    # 生成灵感
    generator = InspirationGenerator()
    inspiration_content = await generator.generate_emotion_inspiration(
        plot_nodes=plot_nodes,
        characters=characters,
        original_text=original_text,
        context=request.context
    )

    # 保存灵感
    inspiration = Inspiration(
        novel_id=request.novel_id,
        type="emotion",
        target_id=request.target_id,
        content=inspiration_content
    )
    db.add(inspiration)
    db.commit()
    db.refresh(inspiration)

    return ApiResponse(
        success=True,
        data=InspirationResponse.model_validate(inspiration).model_dump()
    )


@router.get("/history", response_model=List[InspirationResponse])
async def get_inspiration_history(
    novel_id: str,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """获取灵感历史记录"""
    inspirations = db.query(Inspiration).filter(
        Inspiration.novel_id == novel_id
    ).order_by(Inspiration.created_at.desc()).limit(limit).all()
    return inspirations
