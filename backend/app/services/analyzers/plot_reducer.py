"""
情节分析 Reducer

实现 Map-Reduce 模式中的情节合并 Reduce 阶段
"""

from typing import Dict, Any, List, Optional
import re
import logging

from app.services.map_reduce_analyzer import Reducer, MapResult

logger = logging.getLogger(__name__)


class PlotReducer(Reducer[List[Dict[str, Any]], List[Dict[str, Any]]]):
    """情节分析 Reducer"""

    def __init__(self):
        self._dedup_stats = {}

    def reduce(
        self,
        map_results: List[MapResult[List[Dict[str, Any]]]],
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        合并所有块的情节分析结果

        策略：
        1. 按章节和时间顺序排序
        2. 合并相似标题的情节
        3. 去除重复情节
        4. 智能合并相邻小块情节
        """
        self._dedup_stats = {
            'total_extracted': 0,
            'after_dedup': 0,
            'merged_count': 0
        }

        # 收集所有情节
        all_plots = []
        for map_result in map_results:
            if map_result.result:
                all_plots.extend(map_result.result)

        self._dedup_stats['total_extracted'] = len(all_plots)

        if not all_plots:
            return []

        # 按章节和块索引排序
        all_plots.sort(key=lambda p: (
            self._get_chapter_num(p.get('chapter', 0)),
            p.get('_chunk_index', 0)
        ))

        # 去重
        unique_plots = self._deduplicate_plots(all_plots)

        # 按重要性重新排序（同章节内）
        for chapter_plots in self._group_by_chapter(unique_plots):
            if len(chapter_plots) > 1:
                chapter_plots.sort(key=lambda p: -p.get('importance', 5))

        self._dedup_stats['after_dedup'] = len(unique_plots)
        self._dedup_stats['merged_count'] = len(all_plots) - len(unique_plots)

        logger.info(f"情节合并完成: {self._dedup_stats}")

        return unique_plots

    def _get_chapter_num(self, chapter) -> int:
        """获取章节号"""
        if isinstance(chapter, int):
            return chapter
        if isinstance(chapter, str):
            match = re.search(r'(\d+)', chapter)
            return int(match.group(1)) if match else 0
        return 0

    def _deduplicate_plots(self, plots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去重情节"""
        if not plots:
            return []

        unique = []
        seen_titles = set()

        for plot in plots:
            title = plot.get('title', '').strip()
            normalized_title = re.sub(r'\s+', '', title)

            # 完全重复的标题
            if normalized_title in seen_titles:
                continue

            # 相似度检查
            is_similar = False
            for seen_title in list(seen_titles):
                if self._is_similar_title(normalized_title, seen_title):
                    # 相似时，保留更重要的
                    is_similar = True
                    break

            if not is_similar:
                seen_titles.add(normalized_title)
                # 清理内部字段
                clean_plot = {k: v for k, v in plot.items() if not k.startswith('_')}
                unique.append(clean_plot)

        return unique

    def _is_similar_title(self, title1: str, title2: str) -> bool:
        """检查两个标题是否相似"""
        if not title1 or not title2:
            return False

        # 完全相同
        if title1 == title2:
            return True

        # 包含关系
        if len(title1) > 2 and len(title2) > 2:
            if title1 in title2 or title2 in title1:
                return True

        # 计算字符重叠率
        set1 = set(title1)
        set2 = set(title2)
        intersection = len(set1 & set2)
        union = len(set1 | set2)

        if union > 0:
            similarity = intersection / union
            # 如果重叠率超过 70%，认为相似
            if similarity > 0.7 and len(title1) > 3 and len(title2) > 3:
                return True

        return False

    def _group_by_chapter(self, plots: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """按章节分组"""
        groups = {}
        for plot in plots:
            chapter = self._get_chapter_num(plot.get('chapter', 0))
            if chapter not in groups:
                groups[chapter] = []
            groups[chapter].append(plot)
        return list(groups.values())
