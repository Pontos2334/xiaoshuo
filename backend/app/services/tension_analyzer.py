import logging
from typing import List, Dict, Any
from app.agent.client import ClaudeAgentClient
from app.core.json_utils import JSONParser

logger = logging.getLogger(__name__)

# 常量定义
MAX_TENSION_CONTENT_LENGTH = 20000  # 张力分析最大内容长度
MAX_CLIFFHANGER_CONTENT_LENGTH = 1000  # 悬念建议最大内容长度（章节末尾）
LOW_TENSION_STREAK_THRESHOLD = 5  # 低张力连续章节阈值
LOW_TENSION_LEVEL = 3  # 低张力判定阈值
GOLDEN_THREE_AVG_MIN = 5  # "黄金三章"平均张力最低要求
LOW_CLIFFHANGER_THRESHOLD = 3  # 低悬念分数阈值


class TensionAnalyzer:
    """故事节奏与张力分析服务"""

    def __init__(self):
        self.client = ClaudeAgentClient()
        self.json_parser = JSONParser()

    async def analyze_tension(self, chapters_content: str) -> List[Dict[str, Any]]:
        """
        分析小说各章节的张力与节奏

        给定完整小说内容（或分块内容），AI 逐章分析张力水平。

        Args:
            chapters_content: 小说全文或章节内容

        Returns:
            逐章张力分析列表，每项包含:
            - chapter_number: 章节编号
            - tension_level: 张力等级 (1-10)
            - emotion_tags: 情绪标签列表
            - key_events_summary: 关键事件摘要
            - pacing_note: 节奏点评
            - cliffhanger_score: 悬念分数 (1-10)
            - reader_hook_score: 读者吸引力分数 (1-10，仅前3章)
        """
        if not chapters_content or not chapters_content.strip():
            return []

        truncated_content = chapters_content[:MAX_TENSION_CONTENT_LENGTH]

        prompt = f"""你是一位专业的小说节奏与张力分析师。请逐章分析以下小说内容，评估每一章的张力水平、情绪色彩、节奏感和悬念设置。

小说内容：
{truncated_content}

请对每一章进行详细分析，返回JSON数组，每个元素包含以下字段：
- chapter_number: 章节编号（整数，从1开始）
- tension_level: 张力等级（1-10，1为平淡宁静，10为极度紧张）
- emotion_tags: 情绪标签列表（如 ["紧张", "温馨", "悬疑", "悲伤", "愤怒", "欢乐", "恐惧", "期待"]）
- key_events_summary: 本章关键事件摘要（50-100字）
- pacing_note: 节奏点评（评价本章节奏快慢是否合适，如"节奏紧凑，冲突层层递进"）
- cliffhanger_score: 章末悬念分数（1-10，1为没有悬念，10为极度扣人心弦的悬念）

特别注意：
- 对于前3章（chapter_number为1、2、3），还需要额外包含 reader_hook_score 字段：
  - reader_hook_score: 读者吸引力分数（1-10，10为让读者无法放下书）

只返回JSON数组，不要其他内容。格式示例：
[
  {{"chapter_number": 1, "tension_level": 7, "emotion_tags": ["紧张", "悬疑"], "key_events_summary": "...", "pacing_note": "...", "cliffhanger_score": 8, "reader_hook_score": 9}},
  {{"chapter_number": 2, "tension_level": 5, "emotion_tags": ["温馨", "期待"], "key_events_summary": "...", "pacing_note": "...", "cliffhanger_score": 6, "reader_hook_score": 7}},
  {{"chapter_number": 4, "tension_level": 6, "emotion_tags": ["紧张"], "key_events_summary": "...", "pacing_note": "...", "cliffhanger_score": 4}}
]"""

        response = await self.client.generate(prompt)

        tension_points = self.json_parser.safe_parse_json(response, default=[])
        if not tension_points:
            logger.warning(f"张力分析返回空结果，原始响应: {response[:200]}...")
        else:
            logger.info(f"张力分析完成，共分析 {len(tension_points)} 章")

        return tension_points

    async def detect_pacing_issues(self, tension_points: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        检测节奏问题

        给定按章节排序的张力分析数据，检测以下问题：
        a) 低张力持续区间：连续5章及以上 tension_level < 3
        b) "黄金三章"问题：前3章平均张力 < 5
        c) 缺失悬念：cliffhanger_score < 3 的章节

        Args:
            tension_points: 逐章张力分析列表（由 analyze_tension 返回）

        Returns:
            节奏问题列表，每项包含:
            - issue_type: 问题类型
            - description: 问题描述
            - chapters: 涉及的章节编号列表
            - suggestion: 改进建议
        """
        if not tension_points:
            return []

        issues: List[Dict[str, Any]] = []

        # 按章节编号排序
        sorted_points = sorted(tension_points, key=lambda x: x.get("chapter_number", 0))

        # a) 检测低张力持续区间
        low_tension_streak: List[int] = []
        for point in sorted_points:
            chapter_num = point.get("chapter_number", 0)
            tension = point.get("tension_level", 5)
            if tension < LOW_TENSION_LEVEL:
                low_tension_streak.append(chapter_num)
            else:
                if len(low_tension_streak) >= LOW_TENSION_STREAK_THRESHOLD:
                    issues.append({
                        "issue_type": "low_tension_streak",
                        "description": f"第{low_tension_streak[0]}-{low_tension_streak[-1]}章连续{len(low_tension_streak)}章张力不足（tension_level < {LOW_TENSION_LEVEL}），读者可能感到乏味",
                        "chapters": low_tension_streak.copy(),
                        "suggestion": (
                            f"建议在这{len(low_tension_streak)}章中穿插冲突事件、揭示新信息或引入意外转折，"
                            "打破平淡节奏，重新唤起读者的阅读兴趣。"
                        )
                    })
                low_tension_streak = []

        # 处理末尾的低张力区间
        if len(low_tension_streak) >= LOW_TENSION_STREAK_THRESHOLD:
            issues.append({
                "issue_type": "low_tension_streak",
                "description": f"第{low_tension_streak[0]}-{low_tension_streak[-1]}章连续{len(low_tension_streak)}章张力不足（tension_level < {LOW_TENSION_LEVEL}），读者可能感到乏味",
                "chapters": low_tension_streak.copy(),
                "suggestion": (
                    f"建议在这{len(low_tension_streak)}章中穿插冲突事件、揭示新信息或引入意外转折，"
                    "打破平淡节奏，重新唤起读者的阅读兴趣。"
                )
            })

        # b) 检测"黄金三章"问题
        first_three = [p for p in sorted_points if p.get("chapter_number", 0) in (1, 2, 3)]
        if len(first_three) >= 3:
            avg_tension = sum(p.get("tension_level", 0) for p in first_three) / len(first_three)
            if avg_tension < GOLDEN_THREE_AVG_MIN:
                chapter_numbers = [p.get("chapter_number", 0) for p in first_three]
                issues.append({
                    "issue_type": "golden_three_problem",
                    "description": f"前三章平均张力仅为 {avg_tension:.1f}（低于 {GOLDEN_THREE_AVG_MIN}），未能有效抓住读者",
                    "chapters": chapter_numbers,
                    "suggestion": (
                        "开篇前三章是读者决定是否继续阅读的关键。建议："
                        "1) 在第一章就引入核心冲突或悬念；"
                        "2) 第二章揭示关键信息或制造意外；"
                        "3) 第三章推向一个小高潮或留下强烈悬念。"
                    )
                })

        # c) 检测缺失悬念的章节
        weak_cliffhanger_chapters = []
        for point in sorted_points:
            chapter_num = point.get("chapter_number", 0)
            cliff_score = point.get("cliffhanger_score", 5)
            if cliff_score < LOW_CLIFFHANGER_THRESHOLD:
                weak_cliffhanger_chapters.append(chapter_num)

        if weak_cliffhanger_chapters:
            issues.append({
                "issue_type": "missing_cliffhangers",
                "description": f"第 {', '.join(map(str, weak_cliffhanger_chapters))} 章的章末悬念不足（cliffhanger_score < {LOW_CLIFFHANGER_THRESHOLD}），读者可能缺乏继续阅读的动力",
                "chapters": weak_cliffhanger_chapters,
                "suggestion": (
                    "建议在这些章节末尾加入悬念元素，例如："
                    "1) 揭示一个令人意外的事实；"
                    "2) 让角色面临艰难的抉择；"
                    "3) 引入新的威胁或谜团；"
                    "4) 在关键时刻突然中断叙事。"
                )
            })

        logger.info(f"节奏问题检测完成，发现 {len(issues)} 个问题")
        return issues

    async def suggest_cliffhanger(self, chapter_content: str) -> str:
        """
        为章节结尾提供悬念改进建议

        给定章节末尾内容（最后1000字符），AI 分析并提出悬念优化建议。

        Args:
            chapter_content: 章节末尾内容

        Returns:
            纯文本悬念改进建议
        """
        if not chapter_content or not chapter_content.strip():
            return "无法提供悬念建议：章节内容为空。"

        truncated_content = chapter_content[-MAX_CLIFFHANGER_CONTENT_LENGTH:]

        prompt = f"""你是一位专业的小说创作顾问，擅长设计扣人心弦的章节悬念。请阅读以下章节结尾内容，分析当前结尾的悬念效果，并提出具体的改进建议。

章节结尾内容：
{truncated_content}

请从以下角度分析并给出建议：
1. 当前结尾的悬念效果如何？是否足以让读者想继续阅读？
2. 如果悬念不足，如何在不改变核心情节的前提下增强悬念？
3. 具体建议使用哪些悬念技巧（如信息不对称、时间压力、意外揭示、情感悬念等）
4. 给出一个改写后的结尾示范（可选）

请直接用中文给出建议，不需要JSON格式。"""

        response = await self.client.generate(prompt)
        suggestion = response.strip() if response else "暂无悬念改进建议。"

        logger.info(f"悬念建议生成完成，长度: {len(suggestion)} 字符")
        return suggestion
