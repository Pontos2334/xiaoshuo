from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List

from app.models.database import get_db
from app.models.models import Inspiration, Novel, Character, PlotNode
from app.models.schemas import InspirationRequest, InspirationResponse, ApiResponse
from app.services.inspiration_gen import InspirationGenerator

router = APIRouter()


@router.post("/plot", response_model=ApiResponse)
async def get_plot_inspiration(
    request: InspirationRequest,
    db: Session = Depends(get_db)
):
    """为指定情节生成灵感"""
    # 获取情节节点
    plot_node = None
    if request.target_id:
        plot_node = db.query(PlotNode).filter(PlotNode.id == request.target_id).first()
        if not plot_node:
            raise HTTPException(status_code=404, detail="情节节点不存在")

    # 获取相关上下文
    characters = []
    if plot_node and plot_node.characters:
        characters = db.query(Character).filter(
            Character.id.in_(plot_node.characters)
        ).all()

    # 生成灵感
    generator = InspirationGenerator()
    inspiration_content = await generator.generate_plot_inspiration(
        plot_node=plot_node,
        characters=characters,
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
    novel = None
    if request.novel_id:
        novel = db.query(Novel).filter(Novel.id == request.novel_id).first()

    # 获取所有人物和情节
    characters = db.query(Character).filter(
        Character.novel_id == request.novel_id
    ).all() if request.novel_id else []

    plot_nodes = db.query(PlotNode).filter(
        PlotNode.novel_id == request.novel_id
    ).all() if request.novel_id else []

    # 生成灵感
    generator = InspirationGenerator()
    inspiration_content = await generator.generate_continue_inspiration(
        characters=characters,
        plot_nodes=plot_nodes,
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
    character = None
    if request.target_id:
        character = db.query(Character).filter(Character.id == request.target_id).first()
        if not character:
            raise HTTPException(status_code=404, detail="角色不存在")

    # 生成灵感
    generator = InspirationGenerator()
    inspiration_content = await generator.generate_character_inspiration(
        character=character,
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
    plot_node = None
    if request.target_id:
        plot_node = db.query(PlotNode).filter(PlotNode.id == request.target_id).first()
        if not plot_node:
            raise HTTPException(status_code=404, detail="情节节点不存在")

    # 生成灵感
    generator = InspirationGenerator()
    inspiration_content = await generator.generate_emotion_inspiration(
        plot_node=plot_node,
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
