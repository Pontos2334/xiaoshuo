"""
智能助手 API

提供情节预测、写作建议等智能功能
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import logging

from ..services.novel_assistant.plot_predictor import PlotPredictor
from ..services.novel_assistant.writing_advisor import WritingAdvisor

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
