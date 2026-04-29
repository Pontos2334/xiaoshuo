"""
智能助手 API

提供情节预测、写作建议等智能功能
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
import logging

from ..services.novel_assistant.plot_predictor import PlotPredictor
from ..services.novel_assistant.writing_advisor import WritingAdvisor
from ..services.creative_helper import CreativeHelper
from ..models.database import get_db
from ..models.models import Novel, Character, PlotNode

router = APIRouter(prefix="/assistant", tags=["assistant"])
logger = logging.getLogger(__name__)


class PredictRequest(BaseModel):
    """预测请求"""
    novel_id: str
    plots: List[Dict[str, Any]]
    characters: List[Dict[str, Any]]
    relations: List[Dict[str, Any]]
    context: str = ""
    prediction_type: str = "next_chapter"  # next_chapter/arc_ending/character_fate


class AdviceRequest(BaseModel):
    """建议请求"""
    novel_id: str
    characters: List[Dict[str, Any]]
    plots: List[Dict[str, Any]]
    advice_type: str = "character"  # character/plot


class OutlineRequest(BaseModel):
    """大纲生成请求"""
    premise: str
    genre: str = "玄幻"
    length: int = 100
    style: str = "经典"


class TwistRequest(BaseModel):
    """转折建议请求"""
    current_context: str
    characters: List[str]
    avoid_cliches: bool = True


@router.post("/predict")
async def predict_plot(request: PredictRequest):
    """
    情节预测

    基于现有情节和人物关系，预测故事后续发展
    """
    try:
        predictor = PlotPredictor()
        result = predictor.predict(
            current_plots=request.plots,
            characters=request.characters,
            relations=request.relations,
            context=request.context,
            prediction_type=request.prediction_type
        )

        return {
            "success": True,
            **result.to_dict()
        }
    except Exception as e:
        logger.error(f"情节预测失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/predict/pacing")
async def analyze_pacing(plots: List[Dict[str, Any]]):
    """
    节奏分析

    分析情节的紧张度曲线和节奏
    """
    try:
        predictor = PlotPredictor()
        result = predictor.analyze_plot_pacing(plots)

        return {
            "success": True,
            **result
        }
    except Exception as e:
        logger.error(f"节奏分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/advice")
async def get_advice(request: AdviceRequest):
    """
    写作建议

    分析人物塑造或情节结构，提供专业建议
    """
    try:
        advisor = WritingAdvisor()

        if request.advice_type == "character":
            result = advisor.analyze_character_development(
                characters=request.characters,
                plots=request.plots
            )
        else:
            result = advisor.analyze_plot_structure(plots=request.plots)

        return {
            "success": True,
            **result.to_dict()
        }
    except Exception as e:
        logger.error(f"获取建议失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/outline")
async def generate_outline(request: OutlineRequest):
    """
    生成大纲

    根据故事前提生成完整的小说大纲
    """
    try:
        advisor = WritingAdvisor()
        result = advisor.generate_outline(
            premise=request.premise,
            genre=request.genre,
            length=request.length,
            style=request.style
        )

        return result
    except Exception as e:
        logger.error(f"生成大纲失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/twist")
async def suggest_twist(request: TwistRequest):
    """
    转折建议

    为当前情节提供出人意料的转折建议
    """
    try:
        advisor = WritingAdvisor()
        result = advisor.suggest_plot_twist(
            current_context=request.current_context,
            characters=request.characters,
            avoid_cliches=request.avoid_cliches
        )

        return result
    except Exception as e:
        logger.error(f"转折建议失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class WritersBlockRequest(BaseModel):
    """卡文急救请求"""
    novel_id: str
    context: str = ""
    dilemma: str = ""


class SatisfactionDesignRequest(BaseModel):
    """爽点设计请求"""
    novel_id: str
    type: str = "打脸"  # 打脸/逆袭/装逼/反转
    context: str = ""


@router.post("/writers-block-rescue")
async def writers_block_rescue(request: WritersBlockRequest, db: Session = Depends(get_db)):
    """卡文急救 - 基于当前上下文提供突破建议"""
    try:
        novel = db.query(Novel).filter(Novel.id == request.novel_id).first()
        if not novel:
            raise HTTPException(status_code=404, detail="小说不存在")

        characters = db.query(Character).filter(Character.novel_id == request.novel_id).all()
        plots = db.query(PlotNode).filter(PlotNode.novel_id == request.novel_id).all()

        characters_info = "\n".join([
            f"- {c.name}: {c.story_summary or '无简介'}" for c in characters[:20]
        ])
        plots_info = "\n".join([
            f"- 第{p.chapter}章 {p.title}: {p.summary or ''}" for p in plots[:20]
        ])

        current_context = request.context or ""
        if not current_context and novel.content_path:
            from app.core.file_utils import safe_read_file
            full_content = safe_read_file(novel.content_path)
            current_context = full_content[-3000:] if full_content else ""

        helper = CreativeHelper()
        result = await helper.writers_block_rescue(
            current_context=current_context,
            characters_info=characters_info,
            plots_info=plots_info,
            dilemma=request.dilemma
        )

        return {"success": True, **result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"卡文急救失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/satisfaction-designer")
async def satisfaction_designer(request: SatisfactionDesignRequest, db: Session = Depends(get_db)):
    """爽点设计器 - 设计打脸/逆袭/装逼/反转等爽点场景"""
    valid_types = {"打脸", "逆袭", "装逼", "反转"}
    if request.type not in valid_types:
        raise HTTPException(status_code=400, detail=f"类型必须是: {', '.join(valid_types)}")

    try:
        novel = db.query(Novel).filter(Novel.id == request.novel_id).first()
        if not novel:
            raise HTTPException(status_code=404, detail="小说不存在")

        characters = db.query(Character).filter(Character.novel_id == request.novel_id).all()

        characters_info = "\n".join([
            f"- {c.name}: {c.story_summary or '无简介'}, 性格: {', '.join(c.personality or [])[:50]}" for c in characters[:20]
        ])

        helper = CreativeHelper()
        result = await helper.satisfaction_designer(
            satisfaction_type=request.type,
            characters_info=characters_info,
            context=request.context
        )

        return {"success": True, **result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"爽点设计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
