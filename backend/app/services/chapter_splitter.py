# 章节分割服务

import re
import logging
from typing import List, Tuple, Optional, Dict, Any

logger = logging.getLogger(__name__)


class ChapterSplitter:
    """小说章节分割器"""

    # 中文章节标题模式
    CHINESE_PATTERNS = [
        re.compile(r'^第([一二三四五六七八九十百千\d]+)章'),
        re.compile(r'^第([一二三四五六七八九十百千\d]+)节'),
    ]

    # 英文章节标题模式
    ENGLISH_PATTERNS = [
        re.compile(r'^[Cc]hapter\s*(\d+)', re.IGNORECASE),
        re.compile(r'^CHAPTER\s*(\d+)'),
    ]

    # 数字章节标题模式（第1章、第2章）
    DIGITAL_PATTERNS = [
        re.compile(r'^第(\d+)章'),
        re.compile(r'^第(\d+)节'),
    ]

    # 特殊章节标题（一、二、三...）
    SPECIAL_PATTERNS = [
        re.compile(r'^([一二三四五六七八九十]+)[、\s]'),
        re.compile(r'^【([一二三四五六七八九十百千\d]+)】[、\s]*'),
    ]

    # 中文数字转换映射
    CHINESE_NUM_MAP = {
        '零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
        '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
        '十': 10, '百': 100, '千': 1000,
    }

    def _chinese_to_int(self, chinese_num: str) -> Optional[int]:
        """将中文数字转换为整数"""
        if not chinese_num:
            return None

        # 如果是纯数字，直接返回
        if chinese_num.isdigit():
            return int(chinese_num)

        # 简单的中文数字转换
        result = 0
        temp = 0

        for char in chinese_num:
            if char in self.CHINESE_NUM_MAP:
                num = self.CHINESE_NUM_MAP[char]
                if num >= 10:
                    if temp == 0:
                        temp = 1
                    result += temp * num
                    temp = 0
                else:
                    temp = temp * 10 + num if temp else num
            else:
                return None

        result += temp
        return result if result > 0 else None

    def _parse_chapter_num(self, title: str) -> Optional[int]:
        """从章节标题解析章节号"""
        if not title:
            return None

        # 尝试匹配中文模式
        for pattern in self.CHINESE_PATTERNS:
            match = pattern.search(title)
            if match:
                num_str = match.group(1)
                return self._chinese_to_int(num_str)

        # 尝试匹配英文模式
        for pattern in self.ENGLISH_PATTERNS:
            match = pattern.search(title)
            if match:
                num_str = match.group(1)
                try:
                    return int(num_str)
                except ValueError:
                    return None

        # 尝试匹配数字模式
        for pattern in self.DIGITAL_PATTERNS:
            match = pattern.search(title)
            if match:
                num_str = match.group(1)
                try:
                    return int(num_str)
                except ValueError:
                    return None

        # 尝试匹配特殊模式
        for pattern in self.SPECIAL_PATTERNS:
            match = pattern.search(title)
            if match:
                num_str = match.group(1)
                return self._chinese_to_int(num_str)

        return None

    def split(self, content: str) -> List[Tuple[Optional[int], str, str]]:
        """
        按章节分割小说内容

        Args:
            content: 小说全文内容

        Returns:
            章节列表，每个元素为 (章节号, 章节标题, 章节内容)
        """
        chapters = []
        current_chapter_num = None
        current_title = None
        current_content_lines = []

        all_patterns = (
            self.CHINESE_PATTERNS +
            self.ENGLISH_PATTERNS +
            self.DIGITAL_PATTERNS +
            self.SPECIAL_PATTERNS
        )

        for line in content.split('\n'):
            stripped = line.strip()

            # 检查是否是章节标题
            is_chapter_title = False
            for pattern in all_patterns:
                match = pattern.match(stripped)
                if match:
                    is_chapter_title = True

                    # 保存上一章
                    if current_content_lines:
                        chapter_content = '\n'.join(current_content_lines).strip()
                        if chapter_content:
                            chapters.append((current_chapter_num, current_title or '', chapter_content))

                    # 开始新章节
                    current_chapter_num = self._parse_chapter_num(stripped)
                    current_title = stripped
                    current_content_lines = []
                    break

            # 普通行内容
            if not is_chapter_title and stripped:
                current_content_lines.append(stripped)

        # 添加最后一章（如果有内容）
        if current_content_lines:
            chapter_content = '\n'.join(current_content_lines).strip()
            if chapter_content:
                chapters.append((current_chapter_num, current_title or '', chapter_content))

        return chapters

    def get_chapter_count(self, content: str) -> int:
        """获取小说总章节数"""
        chapters = self.split(content)
        return len(chapters)

    def get_chapter_content(self, content: str, chapter_num: int) -> Optional[str]:
        """获取指定章节的内容"""
        chapters = self.split(content)
        for chapter in chapters:
            if chapter[0] == chapter_num:
                return chapter[2]
        return None

    def get_chapters_from_position(self, content: str, start_chapter: int) -> List[Tuple[Optional[int], str, str]]:
        """
        获取从指定章节开始的所有章节内容

        Args:
            content: 小说全文内容
            start_chapter: 起始章节号

        Returns:
            从起始章节开始的所有章节
        """
        chapters = self.split(content)
        result = []

        for chapter in chapters:
            num = chapter[0]
            if num is not None and num >= start_chapter:
                result.append(chapter)

        return result

    def get_new_chapters(self, content: str, analyzed_chapters: List[int]) -> List[Tuple[Optional[int], str, str]]:
        """
        获取新增的章节（用于增量分析）

        Args:
            content: 小说全文内容
            analyzed_chapters: 已分析的章节号列表

        Returns:
            新增的章节列表
        """
        all_chapters = self.split(content)
        new_chapters = []

        for chapter in all_chapters:
            num = chapter[0]
            if num is not None and num not in analyzed_chapters:
                new_chapters.append(chapter)

        return new_chapters

    def get_content_by_chapter_range(self, content: str, start_chapter: int, end_chapter: int) -> str:
        """
        获取指定章节范围的内容

        Args:
            content: 小说全文内容
            start_chapter: 起始章节号
            end_chapter: 结束章节号

        Returns:
            指定章节范围的完整内容
        """
        chapters = self.split(content)
        result_lines = []

        for chapter in chapters:
            num = chapter[0]
            if num is not None and start_chapter <= num <= end_chapter:
                if chapter[1]:  # 章节标题
                    result_lines.append(chapter[1])
                if chapter[2]:  # 章节内容
                    result_lines.append(chapter[2])
                result_lines.append('')  # 章节分隔

        return '\n'.join(result_lines).strip()

    def get_chapter_summary(self, content: str) -> Dict[int, Dict[str, Any]]:
        """
        获取章节摘要信息

        Args:
            content: 小说全文内容

        Returns:
            字典: {章节号: {'title': 标题, 'word_count': 字数}}
        """
        chapters = self.split(content)
        summary = {}

        for chapter in chapters:
            num = chapter[0]
            if num is not None:
                title = chapter[1]
                content_text = chapter[2]
                word_count = len(content_text)
                summary[num] = {
                    'title': title,
                    'word_count': word_count
                }

        return summary

    def get_max_chapter_num(self, content: str) -> int:
        """获取最大章节号"""
        chapters = self.split(content)
        max_num = 0
        for chapter in chapters:
            if chapter[0] is not None and chapter[0] > max_num:
                max_num = chapter[0]
        return max_num


# 创建全局实例
chapter_splitter = ChapterSplitter()
