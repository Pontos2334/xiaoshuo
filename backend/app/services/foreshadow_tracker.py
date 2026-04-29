"""
伏笔追踪服务

AI 驱动的伏笔识别、追踪与建议系统：
1. 从小说文本中提取伏笔元素
2. 检测伏笔是否已被回收（resolved）
3. 为未回收伏笔提供回收建议
4. 计算过期伏笔（planted 过久未回收）
"""

import logging
from typing import List, Dict, Any

from app.agent.client import ClaudeAgentClient
from app.core.json_utils import JSONParser

logger = logging.getLogger(__name__)

# 常量定义
SHORT_TEXT_THRESHOLD = 15000  # 短文本阈值（字符数）
CHUNK_SIZE = 3000             # 长文本分块大小


class ForeshadowTracker:
    """伏笔追踪服务 - 识别、追踪和回收伏笔"""

    def __init__(self):
        self.client = ClaudeAgentClient()
        self.json_parser = JSONParser()

    # ------------------------------------------------------------------
    # 1. 提取伏笔
    # ------------------------------------------------------------------

    async def extract_foreshadows(
        self,
        content: str,
        chapter_map: dict,
    ) -> List[Dict[str, Any]]:
        """
        从小说内容中提取伏笔元素。

        策略：
        - 短文本（< 15000 字符）：直接发送给 AI 分析
        - 长文本：按 3000 字符分块，逐块分析后合并去重

        Args:
            content: 小说文本内容
            chapter_map: 章节映射字典，格式 {章节标题: 章节编号}
                         用于让 AI 确定伏笔的 plant_chapter

        Returns:
            伏笔列表，每项包含：
            - title: 伏笔标题
            - description: 伏笔描述
            - plant_chapter: 埋设章节（数字或章节标题）
            - plant_description: 埋设时的具体描述
            - related_characters: 相关人物列表
            - importance: 重要程度（1-10）
        """
        if not content or not content.strip():
            return []

        try:
            if len(content) < SHORT_TEXT_THRESHOLD:
                return await self._extract_short(content, chapter_map)
            else:
                return await self._extract_long(content, chapter_map)
        except Exception as e:
            logger.warning(f"提取伏笔失败: {e}")
            return []

    async def _extract_short(
        self,
        content: str,
        chapter_map: dict,
    ) -> List[Dict[str, Any]]:
        """短文本直接发送给 AI 提取伏笔"""

        # 将 chapter_map 格式化为可读文本供 AI 参考
        chapter_info = self._format_chapter_map(chapter_map)

        prompt = f"""请分析以下小说内容，识别其中所有伏笔（foreshadowing）元素。

伏笔是指作者在前期有意埋下的暗示、线索或悬念，用于在后期揭示或回收。

【章节对照表】
{chapter_info}

【小说内容】
{content}

请以 JSON 数组格式返回伏笔列表，每个伏笔包含以下字段：
- title: 伏笔标题（简短概括）
- description: 伏笔描述（什么线索/暗示）
- plant_chapter: 埋设章节（请参照上方章节对照表确定章节编号）
- plant_description: 埋设时的具体文本描述
- related_characters: 相关人物列表
- importance: 重要程度（1-10，10为最关键）

只返回 JSON 数组，不要其他内容。"""

        response = await self.client.generate(prompt)
        return self.json_parser.safe_parse_json(response, default=[])

    async def _extract_long(
        self,
        content: str,
        chapter_map: dict,
    ) -> List[Dict[str, Any]]:
        """长文本分块提取后合并"""

        chunks = [
            content[i : i + CHUNK_SIZE]
            for i in range(0, len(content), CHUNK_SIZE)
        ]

        all_foreshadows: List[Dict[str, Any]] = []
        for idx, chunk in enumerate(chunks):
            try:
                chunk_foreshadows = await self._extract_short(chunk, chapter_map)
                if chunk_foreshadows:
                    all_foreshadows.extend(chunk_foreshadows)
            except Exception as e:
                logger.warning(f"分块 {idx} 伏笔提取失败: {e}")

        # 去重合并（基于 title 相同）
        merged = self._merge_foreshadows(all_foreshadows)
        return merged

    # ------------------------------------------------------------------
    # 2. 检测伏笔回收
    # ------------------------------------------------------------------

    async def check_resolution(
        self,
        content: str,
        foreshadows: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        检测给定伏笔列表中哪些已在小说内容中被回收。

        Args:
            content: 小说文本内容
            foreshadows: 未回收伏笔列表，每项至少包含 title / description

        Returns:
            已回收伏笔列表，每项包含：
            - title: 伏笔标题
            - resolve_chapter: 回收章节（尽可能确定）
            - resolve_description: 回收时的具体描述
        """
        if not content or not foreshadows:
            return []

        try:
            # 将伏笔列表格式化为文本
            foreshadow_list = "\n".join(
                f"{i + 1}. 【{f.get('title', '未知')}】{f.get('description', '')}"
                for i, f in enumerate(foreshadows)
            )

            truncated = content[:SHORT_TEXT_THRESHOLD]

            prompt = f"""请分析以下小说内容，判断给定的伏笔列表中哪些已经在文中被回收（resolved）。

【待检测伏笔】
{foreshadow_list}

【小说内容】
{truncated}

请以 JSON 数组格式返回**已被回收**的伏笔，每项包含：
- title: 伏笔标题（与输入一致）
- resolve_chapter: 回收章节（如果可以确定）
- resolve_description: 回收时的具体描述

只返回 JSON 数组，不要其他内容。如果没有任何伏笔被回收，返回空数组 []。"""

            response = await self.client.generate(prompt)
            return self.json_parser.safe_parse_json(response, default=[])

        except Exception as e:
            logger.warning(f"检测伏笔回收失败: {e}")
            return []

    # ------------------------------------------------------------------
    # 3. 回收建议
    # ------------------------------------------------------------------

    async def suggest_resolution(
        self,
        foreshadow: Dict[str, Any],
        chapters_content: str,
    ) -> str:
        """
        为单个未回收伏笔提供回收建议。

        Args:
            foreshadow: 单个伏笔字典，包含 title / description 等
            chapters_content: 相关章节的文本内容（用于上下文参考）

        Returns:
            文本形式的回收建议（非 JSON）
        """
        if not foreshadow:
            return ""

        try:
            title = foreshadow.get("title", "未知伏笔")
            description = foreshadow.get("description", "")
            plant_chapter = foreshadow.get("plant_chapter", "未知")
            importance = foreshadow.get("importance", "未知")
            related = foreshadow.get("related_characters", [])

            truncated = chapters_content[:SHORT_TEXT_THRESHOLD]

            prompt = f"""你是一位专业的小说创作顾问，请为以下伏笔提供回收建议。

【伏笔信息】
- 标题：{title}
- 描述：{description}
- 埋设章节：{plant_chapter}
- 重要程度：{importance}
- 相关人物：{', '.join(related) if related else '未知'}

【相关章节内容】
{truncated}

请给出以下建议：
1. **回收时机**：建议在什么情节/章节回收这个伏笔？
2. **回收方式**：如何自然地揭示这个伏笔，使其与前面的铺垫呼应？
3. **人物配合**：相关人物在回收场景中应如何表现？
4. **情绪设计**：回收时应传递什么情绪，如何让读者感到满足？

请用中文回答，给出具体、可操作的建议。"""

            return await self.client.generate(prompt)

        except Exception as e:
            logger.warning(f"生成伏笔回收建议失败: {e}")
            return ""

    # ------------------------------------------------------------------
    # 4. 过期伏笔计算（纯计算，无 AI 调用）
    # ------------------------------------------------------------------

    def get_overdue_foreshadows(
        self,
        foreshadows: List[Dict[str, Any]],
        current_chapter: int,
        threshold: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        计算已超过阈值章节数仍未回收的伏笔。

        Args:
            foreshadows: 伏笔列表，每项需包含 status、plant_chapter
            current_chapter: 当前章节编号
            threshold: 允许的最大间隔章节数（默认 50）

        Returns:
            过期伏笔子列表
        """
        overdue = []
        for f in foreshadows:
            status = f.get("status", "")
            if status not in ("planted", "partially_revealed"):
                continue

            plant_chapter = f.get("plant_chapter")
            if plant_chapter is None:
                continue

            try:
                plant_num = int(plant_chapter)
            except (ValueError, TypeError):
                # 如果 plant_chapter 不是数字则跳过
                continue

            if current_chapter - plant_num > threshold:
                overdue.append(f)

        return overdue

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    @staticmethod
    def _format_chapter_map(chapter_map: dict) -> str:
        """将章节映射字典格式化为可读文本"""
        if not chapter_map:
            return "（无章节信息）"

        lines = []
        for title, number in chapter_map.items():
            lines.append(f"- 第{number}章：{title}")
        return "\n".join(lines)

    @staticmethod
    def _merge_foreshadows(
        foreshadows: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """基于 title 去重合并伏笔列表"""
        seen_titles: Dict[str, Dict[str, Any]] = {}
        for f in foreshadows:
            title = f.get("title", "").strip()
            if not title:
                continue
            if title not in seen_titles:
                seen_titles[title] = f
            else:
                # 保留 importance 更高的那个
                existing = seen_titles[title]
                if (f.get("importance") or 0) > (existing.get("importance") or 0):
                    seen_titles[title] = f
        return list(seen_titles.values())
