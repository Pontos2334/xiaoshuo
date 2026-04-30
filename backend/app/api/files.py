from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from fastapi import Depends
import os
import re
from typing import List
from pydantic import BaseModel
import uuid
import logging

from app.models.database import get_db
from app.models.models import Novel, Character, CharacterRelation, PlotNode, PlotConnection, Inspiration
from app.models.schemas import NovelResponse, NovelCreate, ApiResponse
from app.core.file_utils import safe_read_file, safe_write_file
from app.core.security import validate_scan_path

router = APIRouter()
logger = logging.getLogger(__name__)


def _sync_neo4j_novel(novel_id: str, name: str, path: str, content_path: str, chapter_count: int, word_count: int):
    """在 Neo4j 中同步创建 Novel 节点（忽略失败）"""
    try:
        from app.db.repository import novel_repo
        novel_repo.create({
            'name': name,
            'path': path,
            'content_path': content_path,
            'chapter_count': chapter_count,
            'word_count': word_count,
        })
    except Exception as e:
        logger.warning(f"Neo4j 同步 Novel 节点失败（不影响主流程）: {e}")


class FileContent(BaseModel):
    name: str
    content: str
    size: int


class FolderUploadRequest(BaseModel):
    folderName: str
    files: List[FileContent]


@router.get("/novels", response_model=List[NovelResponse])
async def get_novels(db: Session = Depends(get_db)):
    """获取所有小说列表"""
    novels = db.query(Novel).all()
    return novels


# 小说详情、删除、导出 - 使用不同路径避免冲突
@router.get("/novels/{novel_id}/detail", response_model=ApiResponse)
async def get_novel_content(novel_id: str, db: Session = Depends(get_db)):
    """获取小说内容"""
    novel = db.query(Novel).filter(Novel.id == novel_id).first()
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")

    content = ""
    if novel.content_path:
        content = safe_read_file(novel.content_path)

    outline = ""
    if novel.outline_path:
        outline = safe_read_file(novel.outline_path)

    return ApiResponse(
        success=True,
        data={
            "novel": NovelResponse.model_validate(novel).model_dump(),
            "content": content,
            "outline": outline
        }
    )


@router.delete("/novels/{novel_id}", response_model=ApiResponse)
async def delete_novel(novel_id: str, db: Session = Depends(get_db)):
    """删除小说及其所有相关数据"""
    novel = db.query(Novel).filter(Novel.id == novel_id).first()
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")

    novel_name = novel.name
    content_path = novel.content_path

    # 删除关联的数据（按依赖顺序）
    # 1. 删除灵感
    db.query(Inspiration).filter(Inspiration.novel_id == novel_id).delete()

    # 2. 删除情节连接
    db.query(PlotConnection).filter(PlotConnection.novel_id == novel_id).delete()

    # 3. 删除情节节点
    db.query(PlotNode).filter(PlotNode.novel_id == novel_id).delete()

    # 4. 删除人物关系
    db.query(CharacterRelation).filter(CharacterRelation.novel_id == novel_id).delete()

    # 5. 删除人物
    db.query(Character).filter(Character.novel_id == novel_id).delete()

    # 6. 删除小说记录
    db.delete(novel)
    db.commit()

    # 7. 尝试删除文件（如果是在 data/novels 目录下）
    if content_path and "data/novels" in content_path:
        try:
            if os.path.exists(content_path):
                os.remove(content_path)
                logger.info(f"已删除小说文件: {content_path}")
        except Exception as e:
            logger.warning(f"删除小说文件失败: {e}")

    # 8. 清理 Qdrant 向量集合
    try:
        from app.services.vector.qdrant_service import get_qdrant_service
        qdrant = get_qdrant_service()
        qdrant.delete_collection(novel_id)
        logger.info(f"已删除 Qdrant 向量集合: {novel_id}")
    except Exception as e:
        logger.warning(f"删除 Qdrant 向量集合失败: {e}")

    return ApiResponse(
        success=True,
        data={"message": f"已删除小说《{novel_name}》"}
    )


@router.get("/novels/{novel_id}/export")
async def export_novel(novel_id: str, db: Session = Depends(get_db)):
    """导出小说内容"""
    novel = db.query(Novel).filter(Novel.id == novel_id).first()
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")

    content = ""
    if novel.content_path:
        content = safe_read_file(novel.content_path)

    if not content:
        raise HTTPException(status_code=400, detail="小说内容为空")

    # 返回为文本文件下载
    filename = f"{novel.name}.txt"
    return PlainTextResponse(
        content=content,
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.post("/scan", response_model=ApiResponse)
async def scan_folder(path: str, db: Session = Depends(get_db)):
    """扫描指定文件夹，查找小说文件"""
    # 安全校验：验证路径合法性
    try:
        path = validate_scan_path(path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not os.path.exists(path):
        raise HTTPException(status_code=400, detail="文件夹不存在")

    if not os.path.isdir(path):
        raise HTTPException(status_code=400, detail="路径不是文件夹")

    novels = []
    supported_extensions = [".txt", ".md"]

    # 扫描文件夹
    for root, dirs, files in os.walk(path):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in supported_extensions:
                file_path = os.path.join(root, file)
                file_name = os.path.splitext(file)[0]

                # 检查是否已存在
                existing = db.query(Novel).filter(Novel.path == file_path).first()
                if existing:
                    novels.append(NovelResponse.model_validate(existing))
                    continue

                # 创建新小说记录
                try:
                    content = safe_read_file(file_path)
                    word_count = len(content)
                    # 通过正则匹配章节标题估算章节数
                    chapter_matches = re.findall(r'第[一二三四五六七八九十百千\d]+[章回节]', content)
                    chapter_count = len(chapter_matches) if chapter_matches else 1
                except IOError as e:
                    logger.warning(f"跳过无法读取的文件: {file_path}, 错误: {e}")
                    continue

                new_novel = Novel(
                    name=file_name,
                    path=file_path,
                    content_path=file_path,
                    chapter_count=chapter_count,
                    word_count=word_count
                )
                db.add(new_novel)
                db.commit()
                db.refresh(new_novel)
                _sync_neo4j_novel(new_novel.id, new_novel.name, new_novel.path,
                                  new_novel.content_path, new_novel.chapter_count, new_novel.word_count)
                novels.append(NovelResponse.model_validate(new_novel))

    return ApiResponse(
        success=True,
        data={"novels": novels, "count": len(novels)}
    )


@router.post("/upload-folder", response_model=ApiResponse)
async def upload_folder(request: FolderUploadRequest, db: Session = Depends(get_db)):
    """接收从前端上传的文件夹内容，一个文件夹作为一部小说"""
    if not request.files:
        return ApiResponse(success=False, error="文件夹中没有文件")

    # 文件数量限制
    if len(request.files) > 100:
        return ApiResponse(success=False, error="文件数量超过限制（最多100个）")

    # 总大小限制 (50MB)
    MAX_TOTAL_SIZE = 50 * 1024 * 1024
    total_size = sum(f.size for f in request.files)
    if total_size > MAX_TOTAL_SIZE:
        return ApiResponse(success=False, error=f"文件总大小超过限制（{MAX_TOTAL_SIZE // (1024*1024)}MB）")

    # 检查内容不含 null 字节（非文本文件）
    for f in request.files:
        if '\x00' in f.content:
            return ApiResponse(success=False, error=f"文件 '{f.name}' 包含非文本内容")

    # 创建目录保存小说
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "novels")
    os.makedirs(data_dir, exist_ok=True)

    # 合并所有文件内容
    all_content = ""
    total_word_count = 0

    # 按文件名排序，确保章节顺序
    sorted_files = sorted(request.files, key=lambda f: f.name)

    for file in sorted_files:
        all_content += f"\n\n# {file.name}\n\n{file.content}"
        total_word_count += len(file.content)

    # 保存合并后的文件
    novel_path = os.path.join(data_dir, f"{request.folderName}.txt")
    try:
        safe_write_file(novel_path, all_content.strip())
    except IOError as e:
        logger.error(f"保存小说失败: {e}")
        return ApiResponse(success=False, error=f"保存小说失败: {e}")

    # 检查是否已存在
    existing = db.query(Novel).filter(Novel.path == novel_path).first()
    if existing:
        return ApiResponse(
            success=True,
            data=[NovelResponse.model_validate(existing)]
        )

    # 估算章节数
    chapter_matches = re.findall(r'第[一二三四五六七八九十百千\d]+[章回节]', all_content)
    chapter_count = len(chapter_matches) if chapter_matches else len(request.files)

    new_novel = Novel(
        id=str(uuid.uuid4()),
        name=request.folderName,
        path=novel_path,
        content_path=novel_path,
        chapter_count=chapter_count,
        word_count=total_word_count
    )
    db.add(new_novel)
    db.commit()
    db.refresh(new_novel)
    _sync_neo4j_novel(new_novel.id, new_novel.name, new_novel.path,
                      new_novel.content_path, new_novel.chapter_count, new_novel.word_count)

    return ApiResponse(
        success=True,
        data=[NovelResponse.model_validate(new_novel)]
    )
