"""
分析 API

提供带进度追踪的长文本分析接口
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime
import uuid
import logging

from app.models.database import get_db
from app.models.models import Novel
from app.core.file_utils import safe_read_file
from app.core.config import settings
from app.services.map_reduce_analyzer import AnalysisProgress

router = APIRouter()
logger = logging.getLogger(__name__)

# 存储分析任务状态
analysis_tasks: Dict[str, Dict[str, Any]] = {}


class AnalysisStatusResponse(BaseModel):
    """分析状态响应"""
    task_id: str
    status: str
    progress_percent: float
    total_chunks: int
    completed_chunks: int
    estimated_remaining_seconds: Optional[float]
    error: Optional[str] = None


class AnalysisStartResponse(BaseModel):
    """分析启动响应"""
    task_id: str
    status: str
    message: str


def update_task_progress(task_id: str, progress: AnalysisProgress):
    """更新任务进度"""
    if task_id in analysis_tasks:
        analysis_tasks[task_id]['progress'] = progress.to_dict()
        analysis_tasks[task_id]['status'] = progress.status


async def run_character_analysis(
    task_id: str,
    novel_id: str,
    db: Session
):
    """后台运行人物分析"""
    try:
        from app.services.character_analyzer import CharacterAnalyzer

        # 获取小说内容
        novel = db.query(Novel).filter(Novel.id == novel_id).first()
        if not novel:
            analysis_tasks[task_id]['status'] = 'failed'
            analysis_tasks[task_id]['error'] = '小说不存在'
            return

        content = ""
        if novel.content_path:
            content = safe_read_file(novel.content_path)

        if not content:
            analysis_tasks[task_id]['status'] = 'failed'
            analysis_tasks[task_id]['error'] = '小说内容为空'
            return

        # 初始化进度
        analysis_tasks[task_id]['progress'] = {
            'total_chunks': 0,
            'completed_chunks': 0,
            'progress_percent': 0,
            'status': 'in_progress'
        }

        # 创建进度回调
        def progress_callback(p: AnalysisProgress):
            update_task_progress(task_id, p)

        # 执行分析
        analyzer = CharacterAnalyzer(use_map_reduce=True)
        result = await analyzer.analyze(content, progress_callback=progress_callback)

        # 保存结果
        analysis_tasks[task_id]['result'] = result
        analysis_tasks[task_id]['status'] = 'completed'
        analysis_tasks[task_id]['progress']['status'] = 'completed'
        analysis_tasks[task_id]['progress']['progress_percent'] = 100

        logger.info(f"人物分析任务完成: {task_id}, 识别 {len(result)} 个人物")

    except Exception as e:
        logger.error(f"人物分析任务失败: {task_id}, {e}")
        analysis_tasks[task_id]['status'] = 'failed'
        analysis_tasks[task_id]['error'] = str(e)


async def run_plot_analysis(
    task_id: str,
    novel_id: str,
    db: Session
):
    """后台运行情节分析"""
    try:
        from app.services.plot_analyzer import PlotAnalyzer

        # 获取小说内容
        novel = db.query(Novel).filter(Novel.id == novel_id).first()
        if not novel:
            analysis_tasks[task_id]['status'] = 'failed'
            analysis_tasks[task_id]['error'] = '小说不存在'
            return

        content = ""
        outline = ""
        if novel.content_path:
            content = safe_read_file(novel.content_path)
        if novel.outline_path:
            outline = safe_read_file(novel.outline_path)

        if not content:
            analysis_tasks[task_id]['status'] = 'failed'
            analysis_tasks[task_id]['error'] = '小说内容为空'
            return

        # 初始化进度
        analysis_tasks[task_id]['progress'] = {
            'total_chunks': 0,
            'completed_chunks': 0,
            'progress_percent': 0,
            'status': 'in_progress'
        }

        # 创建进度回调
        def progress_callback(p: AnalysisProgress):
            update_task_progress(task_id, p)

        # 执行分析
        analyzer = PlotAnalyzer(use_map_reduce=True)
        result = await analyzer.analyze(content, outline, progress_callback=progress_callback)

        # 保存结果
        analysis_tasks[task_id]['result'] = result
        analysis_tasks[task_id]['status'] = 'completed'
        analysis_tasks[task_id]['progress']['status'] = 'completed'
        analysis_tasks[task_id]['progress']['progress_percent'] = 100

        logger.info(f"情节分析任务完成: {task_id}, 识别 {len(result)} 个情节")

    except Exception as e:
        logger.error(f"情节分析任务失败: {task_id}, {e}")
        analysis_tasks[task_id]['status'] = 'failed'
        analysis_tasks[task_id]['error'] = str(e)


@router.post("/analyze/{novel_id}/async", response_model=AnalysisStartResponse)
async def start_async_analysis(
    novel_id: str,
    analysis_type: str,  # 'character' or 'plot'
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    启动异步分析任务

    Args:
        novel_id: 小说ID
        analysis_type: 分析类型 (character/plot)

    Returns:
        任务ID和状态
    """
    # 检查小说是否存在
    novel = db.query(Novel).filter(Novel.id == novel_id).first()
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")

    if analysis_type not in ['character', 'plot']:
        raise HTTPException(status_code=400, detail="分析类型必须是 character 或 plot")

    # 创建任务
    task_id = str(uuid.uuid4())
    analysis_tasks[task_id] = {
        'task_id': task_id,
        'novel_id': novel_id,
        'type': analysis_type,
        'status': 'started',
        'progress': None,
        'result': None,
        'error': None,
        'created_at': datetime.now().isoformat()
    }

    # 添加后台任务
    if analysis_type == 'character':
        background_tasks.add_task(run_character_analysis, task_id, novel_id, db)
    else:
        background_tasks.add_task(run_plot_analysis, task_id, novel_id, db)

    logger.info(f"启动{analysis_type}分析任务: {task_id}")

    return AnalysisStartResponse(
        task_id=task_id,
        status="started",
        message=f"{analysis_type}分析任务已启动"
    )


@router.get("/status/{task_id}", response_model=AnalysisStatusResponse)
async def get_analysis_status(task_id: str):
    """
    获取分析任务状态

    Args:
        task_id: 任务ID

    Returns:
        任务状态和进度
    """
    if task_id not in analysis_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")

    task = analysis_tasks[task_id]
    progress = task.get('progress', {})

    return AnalysisStatusResponse(
        task_id=task_id,
        status=task.get('status', 'unknown'),
        progress_percent=progress.get('progress_percent', 0),
        total_chunks=progress.get('total_chunks', 0),
        completed_chunks=progress.get('completed_chunks', 0),
        estimated_remaining_seconds=progress.get('estimated_remaining_seconds'),
        error=task.get('error')
    )


@router.get("/result/{task_id}")
async def get_analysis_result(task_id: str):
    """
    获取分析任务结果

    Args:
        task_id: 任务ID

    Returns:
        分析结果
    """
    if task_id not in analysis_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")

    task = analysis_tasks[task_id]

    if task.get('status') != 'completed':
        raise HTTPException(
            status_code=400,
            detail=f"任务未完成，当前状态: {task.get('status')}"
        )

    return {
        "success": True,
        "data": {
            "task_id": task_id,
            "type": task.get('type'),
            "result": task.get('result'),
            "progress": task.get('progress')
        }
    }


@router.post("/cancel/{task_id}")
async def cancel_analysis(task_id: str):
    """
    取消分析任务

    Args:
        task_id: 任务ID

    Returns:
        取消状态
    """
    if task_id not in analysis_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")

    task = analysis_tasks[task_id]

    if task.get('status') in ['completed', 'failed', 'cancelled']:
        raise HTTPException(status_code=400, detail="任务已完成或已取消")

    # 标记为取消
    task['status'] = 'cancelled'
    task['error'] = '用户取消'

    logger.info(f"取消分析任务: {task_id}")

    return {
        "success": True,
        "message": f"任务 {task_id} 已取消"
    }


@router.get("/list")
async def list_analysis_tasks(
    novel_id: Optional[str] = None,
    status: Optional[str] = None
):
    """
    列出分析任务

    Args:
        novel_id: 可选，按小说ID过滤
        status: 可选，按状态过滤

    Returns:
        任务列表
    """
    tasks = []

    for task_id, task in analysis_tasks.items():
        # 过滤条件
        if novel_id and task.get('novel_id') != novel_id:
            continue
        if status and task.get('status') != status:
            continue

        tasks.append({
            'task_id': task_id,
            'novel_id': task.get('novel_id'),
            'type': task.get('type'),
            'status': task.get('status'),
            'created_at': task.get('created_at'),
            'progress_percent': task.get('progress', {}).get('progress_percent', 0)
        })

    # 按创建时间倒序
    tasks.sort(key=lambda t: t.get('created_at', ''), reverse=True)

    return {
        "success": True,
        "data": {
            "tasks": tasks,
            "total": len(tasks)
        }
    }
