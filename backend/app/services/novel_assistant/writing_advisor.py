"""
写作建议器

提供人物塑造、情节节奏、冲突设计等方面的写作建议
"""

import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from anthropic import Anthropic

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class AdviceResult:
    """建议结果"""
    category: str              # 建议类别
    score: float              # 评分 0-100
    analysis: str             # 分析说明
    suggestions: List[str]    # 具体建议
    examples: List[str]       # 示例

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "score": self.score,
            "analysis": self.analysis,
            "suggestions": self.suggestions,
            "examples": self.examples
        }


class WritingAdvisor:
    """
    写作建议器

    分析小说内容，提供专业的写作建议
    """

    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.base_url = base_url or settings.ANTHROPIC_BASE_URL
        self.model = model or settings.CLAUDE_MODEL

        if self.api_key:
            self.client = Anthropic(
                api_key=self.api_key,
                base_url=self.base_url
            )
            logger.info(f"WritingAdvisor 初始化完成: model={self.model}")
        else:
            self.client = None
            logger.warning("未配置 API Key，建议将返回空结果")

    def analyze_character_development(
        self,
        characters: List[Dict[str, Any]],
        plots: List[Dict[str, Any]]
    ) -> AdviceResult:
        """
        分析人物塑造

        评估人物的深度、成长弧线和一致性
        """
        if not self.client:
            return AdviceResult(
                category="人物塑造",
                score=0,
                analysis="API 未配置",
                suggestions=[],
                examples=[]
            )

        # 构建人物信息
        char_info = ""
        for char in characters:
            char_info += f"""
- {char.get('name', '未知')}
  身份: {char.get('basic_info', {}).get('identity', '未指定')}
  性格: {', '.join(char.get('personality', [])) or '未指定'}
  简介: {char.get('story_summary', '无')}
"""

        prompt = f"""作为小说创作顾问，请分析以下人物的塑造质量：

【人物列表】
{char_info}

【分析维度】
1. 人物深度：是否有足够的背景和动机
2. 人物成长：是否有清晰的角色弧线
3. 人物一致性：行为是否符合性格设定
4. 人物冲突：是否有足够的内在和外在冲突
5. 人物关系：关系网络是否丰富有趣

【输出要求】
以 JSON 格式输出：
{{
  "score": 整体评分 (0-100),
  "analysis": "详细分析（200-300字）",
  "suggestions": ["具体的改进建议1", "建议2", ...],
  "examples": ["优秀案例或参考示例"]
}}

请输出 JSON：
"""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )

            content = response.content[0].text
            return self._parse_advice(content, "人物塑造")

        except Exception as e:
            logger.error(f"分析人物塑造失败: {e}")
            return AdviceResult(
                category="人物塑造",
                score=0,
                analysis=f"分析失败: {str(e)}",
                suggestions=[],
                examples=[]
            )

    def analyze_plot_structure(
        self,
        plots: List[Dict[str, Any]]
    ) -> AdviceResult:
        """
        分析情节结构

        评估情节的节奏、张力和逻辑性
        """
        if not self.client:
            return AdviceResult(
                category="情节结构",
                score=0,
                analysis="API 未配置",
                suggestions=[],
                examples=[]
            )

        # 构建情节信息
        plot_info = ""
        for i, plot in enumerate(plots, 1):
            plot_info += f"""
{i}. {plot.get('title', '未命名')}
   章节: {plot.get('chapter', '未知')}
   概述: {plot.get('summary', '无')}
   情绪: {plot.get('emotion', '未知')}
   重要程度: {plot.get('importance', 5)}/10
"""

        prompt = f"""作为小说创作顾问，请分析以下情节结构：

【情节列表】
{plot_info}

【分析维度】
1. 情节节奏：张弛有度，不拖沓也不仓促
2. 情节张力：冲突和悬念的设置
3. 情节逻辑：因果关系清晰，发展合理
4. 情节高潮：是否有足够的高潮点
5. 情节伏笔：是否埋下适当的伏笔

【输出要求】
以 JSON 格式输出：
{{
  "score": 整体评分 (0-100),
  "analysis": "详细分析（200-300字）",
  "suggestions": ["具体的改进建议"],
  "examples": ["优秀情节结构参考"]
}}

请输出 JSON：
"""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )

            content = response.content[0].text
            return self._parse_advice(content, "情节结构")

        except Exception as e:
            logger.error(f"分析情节结构失败: {e}")
            return AdviceResult(
                category="情节结构",
                score=0,
                analysis=f"分析失败: {str(e)}",
                suggestions=[],
                examples=[]
            )

    def generate_outline(
        self,
        premise: str,
        genre: str = "玄幻",
        length: int = 100,
        style: str = "经典"
    ) -> Dict[str, Any]:
        """
        生成小说大纲

        Args:
            premise: 故事前提/核心设定
            genre: 小说类型
            length: 预计字数（万字）
            style: 风格（经典/爽文/慢热等）

        Returns:
            大纲数据
        """
        if not self.client:
            return {
                "success": False,
                "error": "API 未配置"
            }

        prompt = f"""作为小说创作顾问，请根据以下信息生成小说大纲：

【故事前提】
{premise}

【小说类型】
{genre}

【预计长度】
约 {length} 万字

【风格偏好】
{style}

【输出要求】
生成一个完整的三幕式大纲，以 JSON 格式输出：
{{
  "title": "建议的书名",
  "logline": "一句话故事概括",
  "theme": "核心主题",
  "acts": [
    {{
      "name": "第一幕：铺垫",
      "chapters": "第1-20章",
      "description": "这一幕的主要内容",
      "key_events": ["关键事件1", "关键事件2", ...],
      "character_goals": ["人物目标1", ...]
    }},
    ...
  ],
  "main_characters": ["主角", "女主", "反派", ...],
  "world_building": ["世界观设定1", ...],
  "foreshadowing": ["需要埋下的伏笔", ...]
}}
"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )

            content = response.content[0].text

            # 提取 JSON
            json_match = content[content.find('{'):content.rfind('}')+1]
            data = json.loads(json_match)

            return {
                "success": True,
                "outline": data
            }

        except Exception as e:
            logger.error(f"生成大纲失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def suggest_plot_twist(
        self,
        current_context: str,
        characters: List[str],
        avoid_cliches: bool = True
    ) -> Dict[str, Any]:
        """
        建议情节转折

        Args:
            current_context: 当前情节上下文
            characters: 涉及的人物
            avoid_cliches: 是否避免陈词滥调

        Returns:
            转折建议
        """
        if not self.client:
            return {
                "success": False,
                "error": "API 未配置"
            }

        avoid_text = "请避免常见的陈词滥调，如：失忆、误会、车祸等。" if avoid_cliches else ""

        prompt = f"""作为小说创作顾问，请为当前情节提供几个出人意料的转折建议：

【当前情节】
{current_context}

【涉及人物】
{', '.join(characters)}

【要求】
{avoid_text}

【输出格式】
以 JSON 格式输出：
{{
  "twists": [
    {{
      "title": "转折名称",
      "description": "详细描述这个转折",
      "setup": "需要提前做的铺垫",
      "impact": "对后续情节的影响",
      "surprise_level": "惊喜程度 (1-10)"
    }}
  ],
  "recommendation": "最推荐的转折及理由"
}}

请提供 3-5 个不同的转折建议。
"""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=3000,
                messages=[{"role": "user", "content": prompt}]
            )

            content = response.content[0].text
            json_match = content[content.find('{'):content.rfind('}')+1]
            data = json.loads(json_match)

            return {
                "success": True,
                **data
            }

        except Exception as e:
            logger.error(f"建议情节转折失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _parse_advice(self, content: str, category: str) -> AdviceResult:
        """解析建议响应"""
        try:
            json_match = content[content.find('{'):content.rfind('}')+1]
            data = json.loads(json_match)

            return AdviceResult(
                category=category,
                score=float(data.get("score", 0)),
                analysis=data.get("analysis", ""),
                suggestions=data.get("suggestions", []),
                examples=data.get("examples", [])
            )

        except Exception as e:
            logger.warning(f"解析建议失败: {e}")
            return AdviceResult(
                category=category,
                score=0,
                analysis=content[:500],
                suggestions=[],
                examples=[]
            )
