from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import logging

from app.models.database import get_db
from app.models.models import PlotNode, PlotConnection, Novel
from app.models.schemas import (
    PlotNodeResponse,
    PlotNodeCreate,
    PlotNodeUpdate,
    PlotConnectionResponse,
    PlotConnectionCreate,
    PlotConnectionUpdate,
    ApiResponse
)
from app.services.plot_analyzer import PlotAnalyzer
from app.services.chapter_splitter import chapter_splitter
from app.core.file_utils import safe_read_file

router = APIRouter()
logger = logging.getLogger(__name__)


# ========== 情节节点 API ==========

@router.get("", response_model=List[PlotNodeResponse])
async def get_plot_nodes(novel_id: str, db: Session = Depends(get_db)):
    """获取指定小说的情节节点列表"""
    nodes = db.query(PlotNode).filter(PlotNode.novel_id == novel_id).all()
    return nodes


@router.get("/{plot_id}", response_model=PlotNodeResponse)
async def get_plot_node(plot_id: str, db: Session = Depends(get_db)):
    """获取情节节点详情"""
    node = db.query(PlotNode).filter(PlotNode.id == plot_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="情节节点不存在")
    return node


@router.post("/analyze", response_model=ApiResponse)
async def analyze_plots(
    novel_id: str,
    mode: str = Query('full', description="分析模式: full(全量) | incremental(增量)"),
    db: Session = Depends(get_db)
):
    """
    AI分析小说内容，生成情节节点

    Args:
        mode: 分析模式
            - 'full': 全量分析，会重新分析所有内容（默认）
            - 'incremental': 增量分析，只分析新章节，保留用户手动修改的数据
    """
    novel = db.query(Novel).filter(Novel.id == novel_id).first()
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")

    # 获取小说内容
    content = ""
    outline = ""
    if novel.content_path:
        content = safe_read_file(novel.content_path)
    if novel.outline_path:
        outline = safe_read_file(novel.outline_path)

    if not content:
        raise HTTPException(status_code=400, detail="小说内容为空")

    # 获取当前分析版本
    current_version = (novel.analysis_version or 0) + 1

    analyzer = PlotAnalyzer()

    # 根据模式选择分析策略
    if mode == 'incremental' and novel.last_analyzed_chapter and novel.last_analyzed_chapter > 0:
        # 增量分析模式 - 只分析新章节
        logger.info(f"情节增量分析模式: 从第 {novel.last_analyzed_chapter + 1} 章开始")

        new_chapters = chapter_splitter.get_chapters_from_position(content, novel.last_analyzed_chapter + 1)
        if not new_chapters:
            logger.info("没有新章节需要分析")
            all_nodes = db.query(PlotNode).filter(PlotNode.novel_id == novel_id).all()
            return ApiResponse(
                success=True,
                data={
                    'nodes': [PlotNodeResponse.model_validate(n).model_dump() for n in all_nodes],
                    'mode': mode,
                    'analyzed_chapter': novel.last_analyzed_chapter,
                    'message': '没有新章节需要分析'
                }
            )

        # 合并新章节内容
        new_content_parts = []
        for chapter in new_chapters:
            if chapter[2]:  # 章节内容
                new_content_parts.append(chapter[2])
        new_content = '\n\n'.join(new_content_parts)

        # 分析新内容
        plot_nodes = await analyzer.analyze(new_content, outline)

        # 获取现有情节节点
        existing_nodes = db.query(PlotNode).filter(PlotNode.novel_id == novel_id).all()
        existing_titles = {n.title for n in existing_nodes}

        # 过滤掉已存在的情节（避免重复）
        new_plot_nodes = []
        for node in plot_nodes:
            if node.get('title') not in existing_titles:
                new_plot_nodes.append(node)

        plot_nodes = new_plot_nodes
        new_max_chapter = chapter_splitter.get_max_chapter_num(content)
    else:
        # 全量分析模式
        logger.info("情节全量分析模式")

        # 全量分析前，先删除该小说的所有旧情节数据
        logger.info(f"删除小说 {novel_id} 的旧情节数据...")

        # 删除情节连接
        deleted_connections = db.query(PlotConnection).filter(
            PlotConnection.novel_id == novel_id
        ).delete()

        # 删除情节节点
        deleted_nodes = db.query(PlotNode).filter(
            PlotNode.novel_id == novel_id
        ).delete()

        db.commit()
        logger.info(f"已删除 {deleted_nodes} 个情节节点, {deleted_connections} 个情节连接")

        plot_nodes = await analyzer.analyze(content, outline)
        new_max_chapter = chapter_splitter.get_max_chapter_num(content)

    # 标记数据来源
    for node in plot_nodes:
        node['source'] = 'ai'
        node['ai_version'] = current_version

    # 保存到数据库
    for node_data in plot_nodes:
        existing = db.query(PlotNode).filter(
            PlotNode.novel_id == novel_id,
            PlotNode.title == node_data.get("title")
        ).first()

        if existing:
            # 只更新 AI 生成的数据，保留用户修改的
            if existing.source not in ('user', 'ai_modified'):
                for key, value in node_data.items():
                    setattr(existing, key, value)
                existing.source = 'ai'
                existing.ai_version = current_version
        else:
            new_node = PlotNode(
                novel_id=novel_id,
                **node_data
            )
            db.add(new_node)

    # 更新小说的分析进度
    novel.last_analyzed_chapter = new_max_chapter
    novel.last_analyzed_at = datetime.utcnow()
    novel.analysis_version = current_version

    db.commit()

    # 返回所有情节节点
    all_nodes = db.query(PlotNode).filter(PlotNode.novel_id == novel_id).all()
    return ApiResponse(
        success=True,
        data={
            'nodes': [PlotNodeResponse.model_validate(n).model_dump() for n in all_nodes],
            'mode': mode,
            'analyzed_chapter': new_max_chapter,
            'version': current_version,
        }
    )


@router.put("/{plot_id}", response_model=PlotNodeResponse)
async def update_plot_node(
    plot_id: str,
    data: PlotNodeUpdate,
    db: Session = Depends(get_db)
):
    """更新情节节点（用户手动编辑会标记为 ai_modified）"""
    node = db.query(PlotNode).filter(PlotNode.id == plot_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="情节节点不存在")

    update_data = data.model_dump(exclude_unset=True)

    # 标记为用户修改
    update_data['source'] = 'ai_modified'

    for key, value in update_data.items():
        setattr(node, key, value)

    db.commit()
    db.refresh(node)
    return node


@router.delete("/{plot_id}", response_model=ApiResponse)
async def delete_plot_node(plot_id: str, db: Session = Depends(get_db)):
    """删除情节节点"""
    node = db.query(PlotNode).filter(PlotNode.id == plot_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="情节节点不存在")

    db.delete(node)
    db.commit()
    return ApiResponse(success=True, data={"message": "情节节点已删除"})


# ========== 情节连接 API ==========

@router.get("/connections", response_model=List[PlotConnectionResponse])
async def get_connections(novel_id: str, db: Session = Depends(get_db)):
    """获取情节连接列表"""
    connections = db.query(PlotConnection).filter(
        PlotConnection.novel_id == novel_id
    ).all()
    return connections


@router.post("/connections/analyze", response_model=ApiResponse)
async def analyze_connections(novel_id: str, db: Session = Depends(get_db)):
    """AI分析情节连接"""
    novel = db.query(Novel).filter(Novel.id == novel_id).first()
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")

    # 获取所有情节节点
    plot_nodes = db.query(PlotNode).filter(PlotNode.novel_id == novel_id).all()
    if not plot_nodes:
        raise HTTPException(status_code=400, detail="请先分析情节节点")

    # 创建标题到ID的映射
    title_to_id = {node.title: node.id for node in plot_nodes}

    # 辅助函数：通过标题或ID找到真正的情节ID
    def find_plot_id(ref: str) -> str | None:
        if not ref:
            return None
        # 直接匹配ID
        if ref in title_to_id.values():
            return ref
        # 通过标题匹配
        if ref in title_to_id:
            return title_to_id[ref]
        # 模糊匹配（处理 "情节1ID" 或包含标题的情况）
        for title, node_id in title_to_id.items():
            if title in ref or ref.replace('ID', '').replace('情节', '').strip() in title:
                return node_id
        return None

    # 使用AI分析连接
    analyzer = PlotAnalyzer()
    connections = await analyzer.analyze_connections(plot_nodes)

    # 保存到数据库
    saved_count = 0
    for conn_data in connections:
        source_ref = conn_data.get("source_id", "")
        target_ref = conn_data.get("target_id", "")

        # 转换为真正的情节ID
        source_id = find_plot_id(source_ref)
        target_id = find_plot_id(target_ref)

        if not source_id or not target_id:
            logger.warning(f"跳过无效连接: {source_ref} -> {target_ref}")
            continue

        # 检查是否已存在
        existing = db.query(PlotConnection).filter(
            PlotConnection.novel_id == novel_id,
            PlotConnection.source_id == source_id,
            PlotConnection.target_id == target_id
        ).first()

        if existing:
            for key, value in conn_data.items():
                if key not in ["source_id", "target_id"]:
                    setattr(existing, key, value)
        else:
            new_conn = PlotConnection(
                novel_id=novel_id,
                source_id=source_id,
                target_id=target_id,
                connection_type=conn_data.get("connection_type", "next"),
                description=conn_data.get("description", ""),
            )
            db.add(new_conn)
            saved_count += 1

    db.commit()
    logger.info(f"保存了 {saved_count} 个新情节连接")

    # 返回所有连接
    all_connections = db.query(PlotConnection).filter(
        PlotConnection.novel_id == novel_id
    ).all()
    return ApiResponse(
        success=True,
        data=[PlotConnectionResponse.model_validate(c).model_dump() for c in all_connections]
    )


@router.put("/connections/{connection_id}", response_model=PlotConnectionResponse)
async def update_connection(
    connection_id: str,
    data: PlotConnectionUpdate,
    db: Session = Depends(get_db)
):
    """更新情节连接"""
    connection = db.query(PlotConnection).filter(PlotConnection.id == connection_id).first()
    if not connection:
        raise HTTPException(status_code=404, detail="连接不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(connection, key, value)

    db.commit()
    db.refresh(connection)
    return connection


@router.delete("/connections/{connection_id}", response_model=ApiResponse)
async def delete_connection(connection_id: str, db: Session = Depends(get_db)):
    """删除情节连接"""
    connection = db.query(PlotConnection).filter(PlotConnection.id == connection_id).first()
    if not connection:
        raise HTTPException(status_code=404, detail="连接不存在")

    db.delete(connection)
    db.commit()
    return ApiResponse(success=True, data={"message": "连接已删除"})
