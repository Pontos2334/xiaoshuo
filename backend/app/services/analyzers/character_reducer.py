"""
人物分析 Reducer

实现 Map-Reduce 模式中的人物合并 Reduce 阶段
"""

from typing import Dict, Any, List, Optional
import re
import logging

from app.services.map_reduce_analyzer import Reducer, MapResult
from app.services.text_chunker import TextChunk

logger = logging.getLogger(__name__)


class CharacterReducer(Reducer[List[Dict[str, Any]], List[Dict[str, Any]]]):
    """人物分析 Reducer"""

    def __init__(self):
        self._dedup_stats = {}

    def reduce(
        self,
        map_results: List[MapResult[List[Dict[str, Any]]]],
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        合并所有块的人物分析结果

        策略：
        1. 按名字标准化进行分组
        2. 合并同一人物在不同块中的信息
        3. 处理冲突信息（优先保留更详细的信息）
        4. 去重
        """
        self._dedup_stats = {
            'total_extracted': 0,
            'after_dedup': 0,
            'merged_count': 0
        }

        # 收集所有人物
        all_characters = []
        for map_result in map_results:
            if map_result.result:
                all_characters.extend(map_result.result)

        self._dedup_stats['total_extracted'] = len(all_characters)

        if not all_characters:
            return []

        # 按标准化名字分组
        name_groups: Dict[str, List[Dict[str, Any]]] = {}
        for char in all_characters:
            normalized_name = self._normalize_name(char.get('name', ''))
            if normalized_name:
                if normalized_name not in name_groups:
                    name_groups[normalized_name] = []
                name_groups[normalized_name].append(char)

        # 合并每组
        merged_characters = []
        for normalized_name, char_group in name_groups.items():
            merged = self._merge_character_group(char_group)
            merged_characters.append(merged)

        # 按首次出现章节排序
        merged_characters.sort(key=lambda c: self._get_first_chapter_num(c))

        self._dedup_stats['after_dedup'] = len(merged_characters)
        self._dedup_stats['merged_count'] = len(all_characters) - len(merged_characters)

        logger.info(f"人物合并完成: {self._dedup_stats}")

        return merged_characters

    def _normalize_name(self, name: str) -> str:
        """标准化名字用于匹配"""
        if not name:
            return ''
        # 去除空格
        normalized = re.sub(r'\s+', '', name.strip())
        # 去除常见后缀如（师兄）、（师傅）等
        normalized = re.sub(r'[（(][^）)]*[）)]', '', normalized).strip()
        return normalized

    def _merge_character_group(self, chars: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        合并同一人物的多条记录

        策略：
        1. 保留最完整的名字
        2. 合并所有别名（去重）
        3. 合并所有性格特点
        4. 合并所有能力
        5. 合并故事摘要（智能拼接）
        6. 保留最早的首次出现章节
        """
        if len(chars) == 1:
            char = chars[0]
            # 清理内部字段
            return {k: v for k, v in char.items() if not k.startswith('_')}

        # 以信息最完整的记录为基础
        base = max(chars, key=lambda c: self._calc_info_score(c))

        merged = {
            'name': base.get('name', ''),
            'aliases': set(base.get('aliases', []) or []),
            'basic_info': dict(base.get('basic_info', {}) or {}),
            'personality': set(base.get('personality', []) or []),
            'abilities': set(base.get('abilities', []) or []),
            'story_summaries': [base.get('story_summary', '')] if base.get('story_summary') else [],
            'first_appear': base.get('first_appear'),
            'source': 'ai',
        }

        # 合并其他记录
        for char in chars:
            if char is base:
                continue

            # 合并别名
            aliases = char.get('aliases', []) or []
            for alias in aliases:
                if alias:
                    merged['aliases'].add(alias)

            # 合并性格
            personality = char.get('personality', []) or []
            for p in personality:
                if p:
                    merged['personality'].add(p)

            # 合并能力
            abilities = char.get('abilities', []) or []
            for a in abilities:
                if a:
                    merged['abilities'].add(a)

            # 收集故事摘要
            story_summary = char.get('story_summary')
            if story_summary:
                merged['story_summaries'].append(story_summary)

            # 更新基本信息（如果更完整）
            basic_info = char.get('basic_info', {}) or {}
            for key, value in basic_info.items():
                if key not in merged['basic_info'] or not merged['basic_info'].get(key):
                    merged['basic_info'][key] = value

            # 保留最早的章节
            first_appear = char.get('first_appear')
            if first_appear:
                if not merged['first_appear'] or self._compare_chapters(
                    first_appear, merged['first_appear']
                ) < 0:
                    merged['first_appear'] = first_appear

        # 转换 set 为 list
        merged['aliases'] = list(merged['aliases'])
        merged['personality'] = list(merged['personality'])
        merged['abilities'] = list(merged['abilities'])

        # 智能合并故事摘要
        merged['story_summary'] = self._merge_summaries(merged['story_summaries'])
        del merged['story_summaries']

        return merged

    def _calc_info_score(self, char: Dict[str, Any]) -> int:
        """计算人物信息的完整度分数"""
        score = 0

        # 名字长度
        score += len(char.get('name', ''))

        # 别名数量
        score += len(char.get('aliases', []) or []) * 5

        # 基本信息
        basic_info = char.get('basic_info', {}) or {}
        score += len(basic_info) * 10

        # 性格特点
        score += len(char.get('personality', []) or []) * 5

        # 能力
        score += len(char.get('abilities', []) or []) * 5

        # 故事摘要长度
        score += len(char.get('story_summary', '') or '')

        return score

    def _get_first_chapter_num(self, char: Dict[str, Any]) -> int:
        """获取首次出现的章节号"""
        first_appear = char.get('first_appear', '')
        if not first_appear:
            return 999999
        return self._extract_chapter_num(first_appear) or 999999

    def _compare_chapters(self, ch1: str, ch2: str) -> int:
        """比较章节号"""
        num1 = self._extract_chapter_num(ch1)
        num2 = self._extract_chapter_num(ch2)
        if num1 is not None and num2 is not None:
            return num1 - num2
        return 0

    def _extract_chapter_num(self, chapter_str: str) -> Optional[int]:
        """从字符串提取章节号"""
        if not chapter_str:
            return None
        # 尝试提取数字
        match = re.search(r'第?(\d+)章?', str(chapter_str))
        if match:
            return int(match.group(1))
        # 尝试中文数字
        chinese_map = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
                       '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}
        for cn, num in chinese_map.items():
            if cn in chapter_str:
                return num
        return None

    def _merge_summaries(self, summaries: List[str]) -> str:
        """智能合并故事摘要"""
        # 过滤空摘要
        summaries = [s for s in summaries if s and s.strip()]
        if not summaries:
            return ''
        if len(summaries) == 1:
            return summaries[0]

        # 去重并拼接
        unique_summaries = []
        seen = set()
        for s in summaries:
            # 简单的相似度检查
            normalized = re.sub(r'\s+', '', s[:50])
            if normalized not in seen and len(normalized) > 10:
                seen.add(normalized)
                unique_summaries.append(s)

        if not unique_summaries:
            return summaries[0]

        # 最多保留3个摘要，用分号连接
        return '；'.join(unique_summaries[:3])
