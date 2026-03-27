import logging
from typing import List, Dict, Any, Optional, Callable
from app.agent.client import ClaudeAgentClient
from app.core.json_utils import JSONParser

logger = logging.getLogger(__name__)

# 常量定义
MAX_CONTENT_LENGTH = 20000  # 短文本阈值
MAX_OUTLINE_LENGTH = 8000

# Map-Reduce 配置
LONG_TEXT_THRESHOLD = 20000  # 触发 Map-Reduce 的字符阈值
CHUNK_SIZE_PLOT = 4000       # 情节分析块大小
MAX_CONCURRENT_TASKS = 2     # 最大并发任务数（情节分析较复杂）


class PlotAnalyzer:
    """情节分析服务 - 支持 Map-Reduce 长文本处理"""

    def __init__(self, use_map_reduce: bool = True):
        self.agent = ClaudeAgentClient()
        self.json_parser = JSONParser()
        self.use_map_reduce = use_map_reduce

        # 初始化 Map-Reduce 组件
        if use_map_reduce:
            try:
                from app.services.text_chunker import TextChunker, ChunkConfig, ChunkStrategy
                from app.services.map_reduce_analyzer import MapReduceAnalyzer
                from app.services.analyzers.plot_mapper import PlotMapper
                from app.services.analyzers.plot_reducer import PlotReducer

                self.chunker = TextChunker(ChunkConfig(
                    max_chunk_size=CHUNK_SIZE_PLOT,
                    strategy=ChunkStrategy.PARAGRAPH
                ))
                self.map_reduce = MapReduceAnalyzer(
                    mapper=PlotMapper(),
                    reducer=PlotReducer(),
                    chunker=self.chunker,
                    max_concurrent_tasks=MAX_CONCURRENT_TASKS
                )
            except ImportError as e:
                logger.warning(f"Map-Reduce 组件导入失败，使用传统模式: {e}")
                self.use_map_reduce = False

    async def analyze(
        self,
        content: str,
        outline: str = "",
        progress_callback: Optional[Callable[[Any], None]] = None
    ) -> List[Dict[str, Any]]:
        """
        分析小说内容，提取情节节点

        自动选择策略：
        - 短文本（<20000字符）：两阶段分析
        - 长文本：使用 Map-Reduce

        Args:
            content: 小说内容
            outline: 小说大纲
            progress_callback: 进度回调函数（仅 Map-Reduce 模式）

        Returns:
            情节节点列表
        """
        if not content or not content.strip():
            return []

        content_length = len(content)

        # 选择分析策略
        if self.use_map_reduce and content_length >= LONG_TEXT_THRESHOLD:
            logger.info(f"使用 Map-Reduce 模式分析情节 ({content_length} 字符)")
            return await self._analyze_long(content, outline, progress_callback)
        else:
            logger.info(f"使用传统模式分析情节 ({content_length} 字符)")
            return await self._analyze_short(content, outline)

    async def _analyze_short(self, content: str, outline: str = "") -> List[Dict[str, Any]]:
        """
        短文本两阶段分析（原有逻辑）

        分两步进行：
        1. 先让大模型理解整体故事，总结剧情主线和关键转折
        2. 基于理解，提取结构化的情节节点
        """
        truncated_outline = outline[:MAX_OUTLINE_LENGTH] if outline else "暂无大纲"
        truncated_content = content[:MAX_CONTENT_LENGTH]

        # 第一步：让大模型理解整体故事
        understanding_prompt = f"""你是一位专业的小说分析师。请仔细阅读以下小说内容，深入理解故事的整体结构。

小说大纲：
{truncated_outline}

小说内容：
{truncated_content}

请先在脑海中分析：
1. 故事的主线是什么？核心冲突是什么？
2. 有哪些关键的转折点和高潮？
3. 人物关系如何推动情节发展？
4. 情绪的起伏变化是怎样的？

请用一段话（200-300字）总结你对这个故事的理解，包括主线、核心冲突和关键转折。"""

        story_understanding = await self.agent.generate(understanding_prompt)
        logger.info(f"故事理解总结: {story_understanding[:200]}...")

        # 第二步：基于理解，提取结构化的情节节点
        extraction_prompt = f"""基于你对故事的理解：
{story_understanding}

原始内容参考：
{truncated_content[:5000]}

现在请提取主要的情节节点，构建情节时间线。

要求：
1. 按照故事发展顺序提取5-15个关键情节节点
2. 每个节点要体现情节的推进和变化
3. 标注节点之间的因果关系和情绪变化

请以JSON格式返回情节节点列表，每个节点包含：
- title: 情节标题（简洁概括，如"初入江湖"、"师徒决裂"）
- chapter: 所属章节（数字）
- summary: 情节概述（100-150字，说明发生了什么、为什么重要）
- characters: 涉及的主要人物名称列表（2-5个）
- emotion: 主要情绪（紧张/温馨/悲伤/欢乐/愤怒/平静/悬疑）
- importance: 重要程度（1-10，10为最关键的情节点）
- content_ref: 原文关键引用（30字以内）

只返回JSON数组，不要其他内容。格式示例：
[
  {{"title": "穿越降临", "chapter": 1, "summary": "...", "characters": ["李牧崖"], "emotion": "悬疑", "importance": 8, "content_ref": "..."}}
]"""

        response = await self.agent.generate(extraction_prompt)

        plot_nodes = self.json_parser.safe_parse_json(response, default=[])
        if not plot_nodes:
            logger.warning(f"情节分析返回空结果，原始响应: {response[:200]}...")

        logger.info(f"提取了 {len(plot_nodes)} 个情节节点")
        return plot_nodes

    async def _analyze_long(
        self,
        content: str,
        outline: str = "",
        progress_callback: Optional[Callable[[Any], None]] = None
    ) -> List[Dict[str, Any]]:
        """长文本使用 Map-Reduce 分析"""
        try:
            context = {'outline': outline}
            result = await self.map_reduce.analyze(
                text=content,
                context=context,
                progress_callback=progress_callback
            )

            # 添加 source 标记
            for plot in result.result:
                plot['source'] = 'ai'

            logger.info(
                f"Map-Reduce 分析完成: {len(result.result)} 个情节, "
                f"去重统计: {result.deduplication_stats}"
            )

            return result.result

        except Exception as e:
            logger.error(f"Map-Reduce 分析失败，回退到传统模式: {e}")
            return await self._analyze_short(content, outline)

    async def analyze_connections(self, plot_nodes: List[Any]) -> List[Dict[str, Any]]:
        """分析情节之间的连接关系

        基于情节内容，智能判断节点之间的关系类型
        """
        if not plot_nodes or len(plot_nodes) < 2:
            return []

        # 构建情节信息
        plot_info = "\n".join([
            f"- [{n.id}] {n.title}（第{n.chapter}章）: {n.summary[:80]}... 情绪:{n.emotion} 重要度:{n.importance}"
            for n in plot_nodes
        ])

        # 先让模型理解整体情节结构
        structure_prompt = f"""请分析以下情节节点的整体结构：

{plot_info}

请思考：
1. 这些情节如何构成一个完整的故事？
2. 哪些情节是因果关系（A导致B发生）？
3. 哪些情节是伏笔和呼应？
4. 主线情节是什么？支线情节是什么？

请用一段话（150字）描述这个故事的情节结构。"""

        structure_understanding = await self.agent.generate(structure_prompt)
        logger.info(f"情节结构理解: {structure_understanding[:150]}...")

        # 基于理解，提取连接关系
        connection_prompt = f"""基于对情节结构的理解：
{structure_understanding}

情节列表：
{plot_info}

请分析情节之间的连接关系。重点识别：
1. 因果关系：一个情节直接导致另一个情节发生
2. 伏笔关系：早期情节为后期情节埋下伏笔
3. 闪回关系：后期情节回顾早期内容
4. 并行关系：两个情节同时发生或相互对照

返回JSON数组，每个连接包含：
- source_id: 源情节ID
- target_id: 目标情节ID
- connection_type: 连接类型（cause因果/parallel并行/foreshadow伏笔/flashback闪回/next后续）
- description: 连接描述（20-50字，说明两个情节如何关联）

注意：
- 只返回有明确关联的情节对
- 确保ID是有效的情节ID
- 优先识别因果和伏笔关系

格式示例：
[
  {{"source_id": "xxx", "target_id": "yyy", "connection_type": "cause", "description": "..."}}
]"""

        response = await self.agent.generate(connection_prompt)

        connections = self.json_parser.safe_parse_json(response, default=[])
        if not connections:
            logger.warning(f"连接分析返回空结果，原始响应: {response[:200]}...")
        else:
            # 过滤无效的连接
            valid_ids = {n.id for n in plot_nodes}
            valid_connections = []
            for conn in connections:
                source_id = conn.get("source_id", "")
                target_id = conn.get("target_id", "")
                if source_id in valid_ids and target_id in valid_ids and source_id != target_id:
                    valid_connections.append(conn)
            connections = valid_connections
            logger.info(f"提取了 {len(connections)} 个有效连接")

        return connections
