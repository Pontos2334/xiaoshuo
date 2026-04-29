"""
情节预测器

基于现有情节和人物关系，预测故事后续发展
"""

import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class PredictionResult:
    """预测结果"""
    predictions: List[Dict[str, Any]]  # 预测的情节发展
    analysis: str                      # 分析说明
    confidence: float                  # 置信度 0-1
    suggestions: List[str]             # 写作建议

    def to_dict(self) -> Dict[str, Any]:
        return {
            "predictions": self.predictions,
            "analysis": self.analysis,
            "confidence": self.confidence,
            "suggestions": self.suggestions
        }


class PlotPredictor:
    """
    情节预测器

    基于现有情节和人物关系，预测故事后续发展
    """

    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.api_key = api_key or settings.DEEPSEEK_API_KEY
        self.base_url = base_url or settings.DEEPSEEK_BASE_URL
        self.model = model or settings.DEEPSEEK_MODEL

        if self.api_key:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            logger.info(f"PlotPredictor 初始化完成: model={self.model}")
        else:
            self.client = None
            logger.warning("未配置 API Key，预测将返回空结果")

    def predict(
        self,
        current_plots: List[Dict[str, Any]],
        characters: List[Dict[str, Any]],
        relations: List[Dict[str, Any]],
        context: str = "",
        prediction_type: str = "next_chapter"
    ) -> PredictionResult:
        """
        预测情节发展

        Args:
            current_plots: 现有情节列表
            characters: 人物列表
            relations: 人物关系列表
            context: 额外上下文
            prediction_type: 预测类型 (next_chapter/arc_ending/character_fate)

        Returns:
            预测结果
        """
        if not self.client:
            return PredictionResult(
                predictions=[],
                analysis="API 未配置",
                confidence=0.0,
                suggestions=["请配置 API Key 以启用预测功能"]
            )

        # 构建提示词
        prompt = self._build_prediction_prompt(
            current_plots, characters, relations, context, prediction_type
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=3000,
                messages=[{"role": "user", "content": prompt}]
            )

            content = response.choices[0].message.content
            return self._parse_response(content, prediction_type)

        except Exception as e:
            logger.error(f"预测失败: {e}")
            return PredictionResult(
                predictions=[],
                analysis=f"预测失败: {str(e)}",
                confidence=0.0,
                suggestions=[]
            )

    def _build_prediction_prompt(
        self,
        plots: List[Dict[str, Any]],
        characters: List[Dict[str, Any]],
        relations: List[Dict[str, Any]],
        context: str,
        prediction_type: str
    ) -> str:
        """构建预测提示词"""

        # 格式化现有情节
        plot_text = ""
        for i, plot in enumerate(plots[-10:], 1):  # 最近10个情节
            plot_text += f"\n{i}. {plot.get('title', '未命名')}\n"
            plot_text += f"   概述: {plot.get('summary', '无')}\n"
            plot_text += f"   情绪: {plot.get('emotion', '未知')}\n"

        # 格式化人物
        char_text = ""
        for char in characters[:10]:  # 主要人物
            char_text += f"- {char.get('name', '未知')}: {char.get('story_summary', '无简介')}\n"

        # 格式化关系
        rel_text = ""
        for rel in relations[:15]:
            rel_text += f"- {rel.get('source_name', '')} {rel.get('relation_type', '')} {rel.get('target_name', '')}\n"

        # 根据预测类型设置任务描述
        type_descriptions = {
            "next_chapter": "预测下一章可能发生的情节",
            "arc_ending": "预测当前故事线的可能结局",
            "character_fate": "预测某个人物的命运走向"
        }

        task_desc = type_descriptions.get(prediction_type, "预测情节发展")

        prompt = f"""你是一位资深的小说创作顾问，擅长分析故事结构和预测情节发展。

【任务】
{task_desc}

【现有情节】（最近的发展）
{plot_text if plot_text else "（暂无情节信息）"}

【主要人物】
{char_text if char_text else "（暂无人物信息）"}

【人物关系】
{rel_text if rel_text else "（暂无关系信息）"}

【额外上下文】
{context if context else "（无）"}

【输出要求】
请以 JSON 格式输出预测结果：
{{
  "predictions": [
    {{
      "title": "预测情节标题",
      "description": "详细描述这个可能的情节发展",
      "probability": "可能性评分 (1-10)",
      "key_characters": ["涉及的主要人物"],
      "conflicts": ["可能出现的冲突"]
    }}
  ],
  "analysis": "整体分析：当前故事走向、核心冲突、潜在风险",
  "confidence": 整体置信度 (0-1 的小数),
  "suggestions": ["给作者的具体写作建议"]
}}

请输出 3-5 个可能的情节预测，确保逻辑合理、符合人物性格和关系设定。
"""
        return prompt

    def _parse_response(self, content: str, prediction_type: str) -> PredictionResult:
        """解析响应"""
        try:
            # 提取 JSON
            json_match = content[content.find('{'):content.rfind('}')+1]
            data = json.loads(json_match)

            predictions = data.get("predictions", [])
            analysis = data.get("analysis", "")
            confidence = float(data.get("confidence", 0.5))
            suggestions = data.get("suggestions", [])

            return PredictionResult(
                predictions=predictions,
                analysis=analysis,
                confidence=confidence,
                suggestions=suggestions
            )

        except Exception as e:
            logger.warning(f"解析预测结果失败: {e}")
            return PredictionResult(
                predictions=[],
                analysis=content[:500],  # 返回原始内容
                confidence=0.3,
                suggestions=[]
            )

    def analyze_plot_pacing(self, plots: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析情节节奏

        返回紧张度曲线和节奏分析
        """
        if not plots:
            return {"pacing": [], "analysis": "无情节数据"}

        # 简单的紧张度分析
        emotion_scores = {
            "紧张": 0.9, "激烈": 1.0, "悲伤": 0.6, "温馨": 0.2,
            "悬疑": 0.8, "轻松": 0.1, "愤怒": 0.7, "惊喜": 0.5,
            "平淡": 0.3, "恐惧": 0.85, "兴奋": 0.75, "平静": 0.2
        }

        pacing = []
        for plot in plots:
            emotion = plot.get("emotion", "平淡")
            importance = plot.get("importance", 5)
            score = emotion_scores.get(emotion, 0.5) * (importance / 10)
            pacing.append({
                "title": plot.get("title", ""),
                "emotion": emotion,
                "score": round(score, 2),
                "chapter": plot.get("chapter", "")
            })

        # 计算平均值和趋势
        if pacing:
            avg_score = sum(p["score"] for p in pacing) / len(pacing)
            trend = "上升" if pacing[-1]["score"] > pacing[0]["score"] else "下降"
        else:
            avg_score = 0.5
            trend = "平稳"

        return {
            "pacing": pacing,
            "average_tension": round(avg_score, 2),
            "trend": trend,
            "analysis": f"情节节奏{'紧凑' if avg_score > 0.6 else '舒缓'}，紧张度呈{trend}趋势"
        }
