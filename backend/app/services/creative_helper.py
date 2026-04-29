import logging
from typing import Dict, Any
from app.agent.client import ClaudeAgentClient
from app.core.json_utils import JSONParser

logger = logging.getLogger(__name__)

# 合法爽文类型白名单
VALID_SATISFACTION_TYPES = {"打脸", "逆袭", "装逼", "反转"}


class CreativeHelper:
    """创意辅助服务 - 卡文救援、爽点设计、读者期待分析"""

    def __init__(self):
        self.client = ClaudeAgentClient()
        self.json_parser = JSONParser()

    async def writers_block_rescue(
        self,
        current_context: str,
        characters_info: str,
        plots_info: str,
        dilemma: str = "",
    ) -> Dict[str, Any]:
        """
        卡文救援 - 为陷入创作瓶颈的作者提供突破方向

        分析当前创作状态和困境，生成多个可行的突破方向建议。

        Args:
            current_context: 当前正在写作的内容/上下文
            characters_info: 相关角色信息
            plots_info: 相关情节信息
            dilemma: 作者当前面临的具体困境描述（可选）

        Returns:
            包含 suggestions 列表的字典，每条建议包含:
            - direction: 突破方向名称
            - description: 方向描述
            - example_snippet: 示例片段
            - why_it_works: 为什么这个方向有效
        """
        dilemma_section = ""
        if dilemma:
            dilemma_section = f"""【作者困境】
{dilemma}"""

        prompt = f"""你是一位白金级网文创作顾问。作者目前卡文了，需要你提供专业、有实操性的突破建议。

【当前写作内容】
{current_context}

【相关角色】
{characters_info}

【相关情节】
{plots_info}
{dilemma_section}

---

请基于以上信息，为作者提供3个不同的突破方向。每个方向应该是：
- 有创意且令人兴奋的
- 与已有设定自然衔接的
- 具有足够张力吸引读者的
- 操作性强，作者能直接上手写的

请返回JSON对象，格式如下：
{{
  "suggestions": [
    {{
      "direction": "突破方向名称（简短有力，如'暗线浮现'）",
      "description": "详细描述这个方向如何展开（100-200字）",
      "example_snippet": "一段示范性文字片段（50-100字，展示这个方向的写作感觉）",
      "why_it_works": "为什么这个方向能解决当前的卡文问题（50-100字）"
    }}
  ]
}}

确保返回3个风格各异的方向（例如：一个侧重人物、一个侧重情节转折、一个侧重氛围/悬念）。只返回JSON，不要其他内容。"""

        response = await self.client.generate(prompt)
        result = self.json_parser.safe_parse_json(response, default={"suggestions": []})

        if not result or not isinstance(result, dict):
            logger.warning("卡文救援：AI响应解析失败，返回默认值")
            return {"suggestions": []}

        suggestions = result.get("suggestions", [])
        logger.info(f"卡文救援：生成了 {len(suggestions)} 个突破方向")
        return result

    async def satisfaction_designer(
        self,
        satisfaction_type: str,
        characters_info: str,
        context: str,
    ) -> Dict[str, Any]:
        """
        爽点设计器 - 根据指定类型设计一个令人满足的场景

        基于角色信息和上下文，设计打脸/逆袭/装逼/反转类型的爽点场景。

        Args:
            satisfaction_type: 爽文类型，可选值：打脸、逆袭、装逼、反转
            characters_info: 可用角色信息
            context: 当前故事上下文

        Returns:
            场景设计方案，包含:
            - title: 场景标题
            - setup: 铺垫阶段
            - climax: 高潮爆发
            - payoff: 收尾满足感
            - key_characters_involved: 参与角色列表
            - reader_emotion: 读者预期情绪
        """
        if satisfaction_type not in VALID_SATISFACTION_TYPES:
            logger.warning(
                f"爽点设计器：不支持的类型 '{satisfaction_type}'，"
                f"合法值为 {VALID_SATISFACTION_TYPES}"
            )
            return {
                "title": "",
                "setup": "",
                "climax": "",
                "payoff": "",
                "key_characters_involved": [],
                "reader_emotion": "",
            }

        # 为每种类型提供更细致的指导
        type_guides = {
            "打脸": "设计一个角色被轻视/质疑后，以出人意料的方式证明自己的场景。重点：先抑后扬，对手的傲慢与震惊形成强烈对比。",
            "逆袭": "设计一个处于劣势的角色在绝境中翻盘的场景。重点：看似毫无希望，但利用已有伏笔/能力/盟友完成逆转。",
            "装逼": "设计一个角色不经意间展现惊人实力或身份的场景。重点：旁观者的反应层层递进，从无视到震惊到敬畏。",
            "反转": "设计一个颠覆读者预期的情节转折。重点：前文要有伏笔暗示，反转后回头看要觉得'原来如此'而非'强行反转'。",
        }

        guide = type_guides.get(satisfaction_type, "")

        prompt = f"""你是一位白金级网文创作顾问，精通各种爽文套路的设计。

【爽点类型】{satisfaction_type}
【创作指导】{guide}

【可用角色】
{characters_info}

【当前故事上下文】
{context}

---

请基于以上角色和上下文，设计一个精彩的"{satisfaction_type}"场景方案。

要求：
- 必须使用已有的角色，不要凭空创造新角色
- 场景必须自然融入当前故事线
- 铺垫要充分，让读者积攒期待感
- 高潮要爆发力强，让人拍案叫绝
- 收尾要满足感十足，不拖泥带水

请返回JSON对象，格式如下：
{{
  "title": "场景标题（吸引人的名字，如'龙渊现世'）",
  "setup": "铺垫阶段：描述如何营造氛围、积蓄读者期待（100-200字）",
  "climax": "高潮爆发：描述爽点引爆的精彩瞬间（150-250字）",
  "payoff": "收尾满足：描述爆发后的余韵和满足感（80-150字）",
  "key_characters_involved": ["参与的关键角色1", "参与的关键角色2"],
  "reader_emotion": "读者预期情绪（如'大呼过瘾、忍不住拍桌子'）"
}}

只返回JSON，不要其他内容。"""

        response = await self.client.generate(prompt)
        result = self.json_parser.safe_parse_json(
            response,
            default={
                "title": "",
                "setup": "",
                "climax": "",
                "payoff": "",
                "key_characters_involved": [],
                "reader_emotion": "",
            },
        )

        if not result or not isinstance(result, dict):
            logger.warning("爽点设计器：AI响应解析失败，返回默认值")
            return {
                "title": "",
                "setup": "",
                "climax": "",
                "payoff": "",
                "key_characters_involved": [],
                "reader_emotion": "",
            }

        logger.info(f"爽点设计器：'{satisfaction_type}'场景方案生成完成 - {result.get('title', '无标题')}")
        return result

    async def reader_expectation_analyzer(
        self,
        recent_chapters: str,
        characters_info: str,
        plots_info: str,
    ) -> Dict[str, Any]:
        """
        读者期待分析器 - 分析读者最可能想要看到的内容

        基于近期章节、角色信息和情节走向，预测读者期待和潜在风险。

        Args:
            recent_chapters: 近期章节内容
            characters_info: 角色信息
            plots_info: 情节信息

        Returns:
            分析结果，包含:
            - top_expectations: 读者最期待的后续发展列表
              - what: 期待内容
              - confidence: 置信度 (0-1)
              - why: 为什么读者会有这个期待
            - risk_areas: 潜在的风险/雷区列表
        """
        prompt = f"""你是一位资深的网文读者心理分析师，同时也深谙网文创作的规律。你的任务是分析当前小说的走向，预测读者最期待看到什么，以及哪些地方可能引发读者不满。

【近期章节内容】
{recent_chapters}

【角色信息】
{characters_info}

【情节信息】
{plots_info}

---

请从读者的角度分析以下内容：

【一、读者期待分析】
基于当前情节走向、人物关系和网文读者的阅读心理，读者最可能在期待什么？
请给出3-5个最强烈的期待，按强烈程度排序。

每个期待需要包含：
- what: 读者期待的具体内容（如"主角复仇成功"、"某配角身份揭晓"）
- confidence: 你判断这个期待的置信度（0到1之间，越接近1越确定）
- why: 为什么读者会产生这个期待（基于哪些情节铺垫或网文套路）

【二、风险区域】
哪些地方可能让读者失望或产生不满？
- 如未兑现的伏笔太久没有回收
- 如某个读者喜爱的角色被冷落太久
- 如情节走向可能落入俗套
- 如重要冲突可能被轻率解决

请返回JSON对象，格式如下：
{{
  "top_expectations": [
    {{
      "what": "期待的具体内容",
      "confidence": 0.85,
      "why": "为什么读者期待这个"
    }}
  ],
  "risk_areas": [
    "风险点1的描述",
    "风险点2的描述"
  ]
}}

只返回JSON，不要其他内容。"""

        response = await self.client.generate(prompt)
        default_result: Dict[str, Any] = {
            "top_expectations": [],
            "risk_areas": [],
        }
        result = self.json_parser.safe_parse_json(response, default=default_result)

        if not result or not isinstance(result, dict):
            logger.warning("读者期待分析器：AI响应解析失败，返回默认值")
            return default_result

        expectations = result.get("top_expectations", [])
        risks = result.get("risk_areas", [])
        logger.info(
            f"读者期待分析器：分析完成，"
            f"发现 {len(expectations)} 个期待点，"
            f"{len(risks)} 个风险区域"
        )
        return result
