"""
大纲管理服务

提供层级式大纲的 AI 生成与同步功能：
- Level 0: 总纲（基于核心设定生成）
- Level 1: 卷/章节大纲（基于总纲拆分）
- Level 2: 章节细纲（基于章节大纲展开为场景/节拍）
"""

import logging
from typing import Any, Dict, List

from app.agent.client import ClaudeAgentClient
from app.core.json_utils import JSONParser

logger = logging.getLogger(__name__)


class OutlineService:
    """层级式大纲管理服务"""

    def __init__(self):
        self.client = ClaudeAgentClient()
        self.json_parser = JSONParser()

    # ------------------------------------------------------------------
    # Level 0 — 总纲
    # ------------------------------------------------------------------

    async def generate_master_outline(
        self,
        premise: str,
        genre: str = "",
        target_length: str = "",
    ) -> List[Dict[str, Any]]:
        """
        基于小说核心设定生成总纲（Level 0）。

        Args:
            premise: 小说的核心设定/故事梗概
            genre: 题材类型（如"玄幻""都市""悬疑"），可为空
            target_length: 目标篇幅描述（如"200万字""三卷本"），可为空

        Returns:
            包含 {title, content, chapter_range, sort_order} 的列表
        """
        genre_hint = f"题材类型为【{genre}】" if genre else "题材类型不限"
        length_hint = f"目标篇幅为【{target_length}】" if target_length else "篇幅不限"

        prompt = f"""你是一位资深网文大纲策划师，精通长篇连载的节奏把控与读者心理。

【任务】
请根据以下核心设定，生成一部小说的总纲。

【核心设定】
{premise}

【附加信息】
{genre_hint}，{length_hint}

【要求】
1. 遵循网文创作规律，注意节奏把控，适合长篇连载，考虑读者期待。
2. 将整部作品拆分为若干大卷/大阶段，每卷给出标题和概括性内容。
3. 每卷标注预估的章节范围（如"第1-50章"）。
4. 按故事发展顺序排列，注意起承转合的节奏：
   - 开篇卷：快速建立世界观与核心矛盾，吸引读者
   - 发展卷：层层递进，铺设伏笔，人物成长
   - 高潮卷：矛盾爆发，大场面与情感巅峰
   - 收束卷：收束伏笔，升华主题，余韵留白
5. 每卷内容描述控制在 80-150 字。

请以 JSON 数组格式返回，每个元素包含：
- title: 卷名（如"初入江湖篇""王城风云篇"）
- content: 本卷内容概括
- chapter_range: 章节范围（如"第1-50章"）
- sort_order: 排序序号（从1开始）

只返回 JSON 数组，不要其他内容。"""

        try:
            response = await self.client.generate(prompt)
            result = self.json_parser.safe_parse_json(response, default=[])
            if not result:
                logger.warning("总纲生成返回空结果，原始响应: %s", response[:200])
            else:
                logger.info("总纲生成完成，共 %d 卷", len(result))
            return result
        except Exception as e:
            logger.error("总纲生成失败: %s", e)
            return []

    # ------------------------------------------------------------------
    # Level 1 — 卷/章节大纲
    # ------------------------------------------------------------------

    async def breakdown_volume(
        self,
        volume_content: str,
        characters_info: str,
        existing_plots: str,
    ) -> List[Dict[str, Any]]:
        """
        将一卷的总纲内容拆分为章节级别大纲（Level 1）。

        Args:
            volume_content: 该卷的总纲内容描述
            characters_info: 相关人物信息摘要
            existing_plots: 已有的情节节点信息

        Returns:
            包含 {title, content, chapter_range, sort_order} 的列表
        """
        prompt = f"""你是一位经验丰富的网文章节策划师，擅长把控单卷节奏。

【任务】
请将以下卷级大纲拆分为详细的章节级大纲。

【本卷总纲】
{volume_content}

【相关人物】
{characters_info or "暂无人物信息"}

【已有情节】
{existing_plots or "暂无已有情节"}

【要求】
1. 遵循网文创作规律，每章内容需有明确的推进或转折，保持读者期待感。
2. 每章大纲需包含：章节标题、本章核心事件/冲突/转折的内容概括。
3. 注意节奏把控：
   - 每 3-5 章设置一个小高潮或悬念
   - 张弛有度，战斗与日常交替，紧张与舒缓结合
   - 章末设置钩子（悬念/伏笔），引导读者追读
4. 适合长篇连载，考虑前后章节的呼应与伏笔。
5. 每章内容概括控制在 60-120 字。

请以 JSON 数组格式返回，每个元素包含：
- title: 章节标题（如"第一章 命运的开端"）
- content: 本章内容概括
- chapter_range: 章节编号（如"第1章"）
- sort_order: 排序序号（从1开始）

只返回 JSON 数组，不要其他内容。"""

        try:
            response = await self.client.generate(prompt)
            result = self.json_parser.safe_parse_json(response, default=[])
            if not result:
                logger.warning("章节大纲拆分返回空结果，原始响应: %s", response[:200])
            else:
                logger.info("章节大纲拆分完成，共 %d 章", len(result))
            return result
        except Exception as e:
            logger.error("章节大纲拆分失败: %s", e)
            return []

    # ------------------------------------------------------------------
    # Level 2 — 章节细纲（场景/节拍）
    # ------------------------------------------------------------------

    async def expand_chapter(
        self,
        chapter_outline: str,
        characters_info: str,
    ) -> List[Dict[str, Any]]:
        """
        将章节大纲展开为详细的场景/节拍细纲（Level 2）。

        Args:
            chapter_outline: 章节大纲内容
            characters_info: 相关人物信息

        Returns:
            包含 {title, content, sort_order} 的列表
        """
        prompt = f"""你是一位专业的网文细纲编剧，擅长将章节大纲细化为可执行的场景节拍。

【任务】
请将以下章节大纲展开为详细的场景/节拍细纲。

【章节大纲】
{chapter_outline}

【相关人物】
{characters_info or "暂无人物信息"}

【要求】
1. 遵循网文创作规律，每个场景/节拍需有明确的写作目标。
2. 将一章拆分为 3-6 个场景或节拍，涵盖：
   - 场景描写（环境/氛围）
   - 人物行动（对话/心理/动作）
   - 情节推进（信息揭示/冲突升级/转折）
   - 情绪节奏（起承转合的微节奏）
3. 注意节奏把控：开场抓人、中段推进、结尾留钩子。
4. 适合长篇连载，考虑与前后章节的衔接。
5. 每个场景/节拍描述控制在 50-100 字，明确写作者需要呈现什么。
6. 考虑读者期待，在适当位置设置悬念或反转。

请以 JSON 数组格式返回，每个元素包含：
- title: 场景/节拍标题（如"场景一：雨夜相遇"）
- content: 详细内容描述（写作者可直接参考的内容要点）
- sort_order: 排序序号（从1开始）

只返回 JSON 数组，不要其他内容。"""

        try:
            response = await self.client.generate(prompt)
            result = self.json_parser.safe_parse_json(response, default=[])
            if not result:
                logger.warning("章节细纲展开返回空结果，原始响应: %s", response[:200])
            else:
                logger.info("章节细纲展开完成，共 %d 个场景", len(result))
            return result
        except Exception as e:
            logger.error("章节细纲展开失败: %s", e)
            return []

    # ------------------------------------------------------------------
    # 大纲与实际章节的同步比对
    # ------------------------------------------------------------------

    async def sync_with_chapters(
        self,
        outline_nodes: List[Dict[str, Any]],
        chapters: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        比较大纲节点与实际章节，找出匹配和差异。

        Args:
            outline_nodes: 大纲节点列表，每个节点至少包含 id、title、content
            chapters: 实际章节列表，每个章节至少包含 id、title、content

        Returns:
            {{
                matched: [{{outline_id, chapter_id}}],
                unmatched_outlines: [...],
                unmatched_chapters: [...]
            }}
        """
        if not outline_nodes and not chapters:
            return {
                "matched": [],
                "unmatched_outlines": [],
                "unmatched_chapters": [],
            }

        outline_summary = "\n".join([
            f"- [ID:{n.get('id', '?')}] {n.get('title', '')}: {n.get('content', '')[:80]}"
            for n in outline_nodes
        ])

        chapter_summary = "\n".join([
            f"- [ID:{c.get('id', '?')}] {c.get('title', '')}: {c.get('content', '')[:80]}"
            for c in chapters
        ])

        prompt = f"""你是一位细心的小说编辑，负责核对大纲与实际章节的对应关系。

【任务】
请比对以下大纲节点与实际章节，找出它们之间的匹配关系。

【大纲节点】
{outline_summary or "（无大纲节点）"}

【实际章节】
{chapter_summary or "（无实际章节）"}

【要求】
1. 根据标题相似度和内容相关性进行匹配。
2. 一个大纲节点最多匹配一个章节，一个章节最多匹配一个大纲节点。
3. 无法匹配的节点和章节分别列出。
4. 遵循网文创作规律，考虑章节标题可能在写作过程中有调整。

请以 JSON 格式返回，结构如下：
{{
    "matched": [
        {{"outline_id": "大纲节点ID", "chapter_id": "章节ID"}}
    ],
    "unmatched_outlines": [
        {{"id": "大纲节点ID", "title": "标题", "content": "内容摘要"}}
    ],
    "unmatched_chapters": [
        {{"id": "章节ID", "title": "标题", "content": "内容摘要"}}
    ]
}}

只返回 JSON，不要其他内容。"""

        try:
            response = await self.client.generate(prompt)
            result = self.json_parser.safe_parse_json(response, default=None)

            if result is None:
                logger.warning("大纲同步比对返回空结果，原始响应: %s", response[:200])
                return {
                    "matched": [],
                    "unmatched_outlines": outline_nodes,
                    "unmatched_chapters": chapters,
                }

            # 确保 result 包含全部三个键
            matched = result.get("matched", [])
            unmatched_outlines = result.get("unmatched_outlines", [])
            unmatched_chapters = result.get("unmatched_chapters", [])

            logger.info(
                "大纲同步完成: 匹配 %d 对, 未匹配大纲 %d 个, 未匹配章节 %d 个",
                len(matched),
                len(unmatched_outlines),
                len(unmatched_chapters),
            )

            return {
                "matched": matched,
                "unmatched_outlines": unmatched_outlines,
                "unmatched_chapters": unmatched_chapters,
            }
        except Exception as e:
            logger.error("大纲同步比对失败: %s", e)
            return {
                "matched": [],
                "unmatched_outlines": outline_nodes,
                "unmatched_chapters": chapters,
            }
