"""
Map-Reduce 分析框架

用于处理长文本的分布式分析：
1. Map: 对每个文本块独立分析
2. Shuffle: 中间处理（可选）
3. Reduce: 合并分析结果
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable, TypeVar, Generic
import asyncio
import logging
from datetime import datetime

from .text_chunker import TextChunker, ChunkConfig, ChunkStrategy, TextChunk

logger = logging.getLogger(__name__)

T = TypeVar('T')  # Map result type
R = TypeVar('R')  # Reduce result type


@dataclass
class AnalysisProgress:
    """分析进度"""
    total_chunks: int
    completed_chunks: int
    current_chunk_index: int
    started_at: datetime
    estimated_remaining_seconds: Optional[float] = None
    status: str = "in_progress"  # in_progress, completed, failed
    error: Optional[str] = None

    @property
    def progress_percent(self) -> float:
        if self.total_chunks == 0:
            return 0
        return (self.completed_chunks / self.total_chunks) * 100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_chunks": self.total_chunks,
            "completed_chunks": self.completed_chunks,
            "current_chunk_index": self.current_chunk_index,
            "progress_percent": round(self.progress_percent, 1),
            "started_at": self.started_at.isoformat(),
            "estimated_remaining_seconds": self.estimated_remaining_seconds,
            "status": self.status,
            "error": self.error
        }


@dataclass
class MapResult(Generic[T]):
    """Map 阶段结果"""
    chunk_index: int
    chunk: TextChunk
    result: T
    processing_time_ms: float
    error: Optional[str] = None


@dataclass
class ReduceResult(Generic[R]):
    """Reduce 阶段结果"""
    result: R
    total_chunks_processed: int
    total_processing_time_ms: float
    deduplication_stats: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result": self.result,
            "total_chunks_processed": self.total_chunks_processed,
            "total_processing_time_ms": round(self.total_processing_time_ms, 2),
            "deduplication_stats": self.deduplication_stats
        }


class Mapper(ABC, Generic[T]):
    """Map 抽象基类"""

    @abstractmethod
    async def map(self, chunk: TextChunk, context: Dict[str, Any]) -> T:
        """
        处理单个文本块

        Args:
            chunk: 文本块
            context: 上下文信息（如小说ID、已有数据等）

        Returns:
            处理结果
        """
        pass


class Reducer(ABC, Generic[T, R]):
    """Reduce 抽象基类"""

    @abstractmethod
    def reduce(self, map_results: List[MapResult[T]], context: Dict[str, Any]) -> R:
        """
        合并所有 Map 结果

        Args:
            map_results: 所有 Map 阶段的结果
            context: 上下文信息

        Returns:
            合并后的最终结果
        """
        pass


class MapReduceAnalyzer(Generic[T, R]):
    """
    Map-Reduce 分析器

    支持并行处理、进度追踪、错误恢复
    """

    def __init__(
        self,
        mapper: Mapper[T],
        reducer: Reducer[T, R],
        chunker: TextChunker = None,
        max_concurrent_tasks: int = 3
    ):
        self.mapper = mapper
        self.reducer = reducer
        self.chunker = chunker or TextChunker()
        self.max_concurrent_tasks = max_concurrent_tasks
        self._progress: Optional[AnalysisProgress] = None
        self._is_cancelled = False

    async def analyze(
        self,
        text: str,
        chunk_config: ChunkConfig = None,
        context: Dict[str, Any] = None,
        progress_callback: Optional[Callable[[AnalysisProgress], None]] = None
    ) -> ReduceResult[R]:
        """
        执行 Map-Reduce 分析

        Args:
            text: 待分析文本
            chunk_config: 分块配置
            context: 上下文信息
            progress_callback: 进度回调函数

        Returns:
            分析结果
        """
        self._is_cancelled = False
        context = context or {}

        # 1. 分块
        chunk_result = self.chunker.chunk(text, chunk_config)
        chunks = chunk_result.chunks

        if not chunks:
            logger.warning("没有可分析的文本块")
            return ReduceResult(
                result=[],
                total_chunks_processed=0,
                total_processing_time_ms=0
            )

        # 初始化进度
        self._progress = AnalysisProgress(
            total_chunks=len(chunks),
            completed_chunks=0,
            current_chunk_index=0,
            started_at=datetime.now()
        )

        logger.info(
            f"开始 Map-Reduce 分析: {len(chunks)} 个块, "
            f"最大并发={self.max_concurrent_tasks}"
        )

        # 2. Map 阶段（并行处理）
        map_results = await self._map_phase(
            chunks,
            context,
            progress_callback
        )

        if self._is_cancelled:
            self._progress.status = "cancelled"
            raise asyncio.CancelledError("Analysis was cancelled")

        # 3. Reduce 阶段
        final_result = self.reducer.reduce(map_results, context)

        # 4. 构建结果
        total_time = (datetime.now() - self._progress.started_at).total_seconds() * 1000
        self._progress.status = "completed"

        logger.info(
            f"Map-Reduce 分析完成: "
            f"处理 {len(map_results)} 个块, "
            f"耗时 {total_time:.0f}ms"
        )

        return ReduceResult(
            result=final_result,
            total_chunks_processed=len(map_results),
            total_processing_time_ms=total_time,
            deduplication_stats=getattr(self.reducer, '_dedup_stats', {})
        )

    async def _map_phase(
        self,
        chunks: List[TextChunk],
        context: Dict[str, Any],
        progress_callback: Optional[Callable[[AnalysisProgress], None]]
    ) -> List[MapResult[T]]:
        """Map 阶段：并行处理所有块"""
        semaphore = asyncio.Semaphore(self.max_concurrent_tasks)
        results: List[MapResult[T]] = []
        lock = asyncio.Lock()

        async def process_chunk(chunk: TextChunk) -> Optional[MapResult[T]]:
            if self._is_cancelled:
                return None

            async with semaphore:
                start_time = datetime.now()
                self._progress.current_chunk_index = chunk.index

                try:
                    result = await self.mapper.map(chunk, context)
                    processing_time = (datetime.now() - start_time).total_seconds() * 1000

                    map_result = MapResult(
                        chunk_index=chunk.index,
                        chunk=chunk,
                        result=result,
                        processing_time_ms=processing_time
                    )

                    async with lock:
                        results.append(map_result)
                        self._progress.completed_chunks += 1

                        # 估算剩余时间
                        if self._progress.completed_chunks > 1:
                            elapsed = (datetime.now() - self._progress.started_at).total_seconds()
                            avg_time = elapsed / self._progress.completed_chunks
                            remaining = (self._progress.total_chunks - self._progress.completed_chunks) * avg_time
                            self._progress.estimated_remaining_seconds = remaining

                    if progress_callback:
                        progress_callback(self._progress)

                    logger.debug(
                        f"块 {chunk.index + 1}/{len(chunks)} 处理完成, "
                        f"耗时 {processing_time:.0f}ms"
                    )

                    return map_result

                except Exception as e:
                    logger.error(f"Map failed for chunk {chunk.index}: {e}")
                    processing_time = (datetime.now() - start_time).total_seconds() * 1000

                    async with lock:
                        self._progress.completed_chunks += 1

                    if progress_callback:
                        progress_callback(self._progress)

                    return MapResult(
                        chunk_index=chunk.index,
                        chunk=chunk,
                        result=None,
                        processing_time_ms=processing_time,
                        error=str(e)
                    )

        # 并行执行所有任务
        tasks = [process_chunk(chunk) for chunk in chunks]
        await asyncio.gather(*tasks, return_exceptions=True)

        # 过滤有效结果
        valid_results = [r for r in results if r is not None and r.error is None]
        error_count = len(results) - len(valid_results)

        if error_count > 0:
            logger.warning(f"Map 阶段有 {error_count} 个块处理失败")

        return valid_results

    def cancel(self):
        """取消分析"""
        self._is_cancelled = True
        if self._progress:
            self._progress.status = "cancelled"

    def get_progress(self) -> Optional[AnalysisProgress]:
        """获取当前进度"""
        return self._progress


class SimpleMapReduceAnalyzer(MapReduceAnalyzer[List[Dict[str, Any]], List[Dict[str, Any]]]):
    """
    简化的 Map-Reduce 分析器

    直接返回合并后的列表结果
    """

    pass
