"""章节管理 API"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
import json

from app.models.database import get_db
from app.models.models import Novel, Chapter
from app.models.schemas import (
    ChapterResponse, ChapterDetailResponse, ChapterUpdate,
    ChapterReorder, ApiResponse
)
from app.services.chapter_splitter import chapter_splitter
from app.core.file_utils import safe_read_file

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("", response_model=List[ChapterResponse])
async def get_chapters(novel_id: str, db: Session = Depends(get_db)):
    """获取小说章节列表（不含内容，用于导航）"""
    novel = db.query(Novel).filter(Novel.id == novel_id).first()
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")

    chapters = db.query(Chapter).filter(
        Chapter.novel_id == novel_id
    ).order_by(Chapter.chapter_number).all()

    # 如果数据库中没有章节数据，尝试从文件中解析
    if not chapters and novel.content_path:
        content = safe_read_file(novel.content_path)
        if content:
            chapters = _parse_and_save_chapters(novel_id, content, db)

    return chapters


@router.get("/{chapter_id}", response_model=ChapterDetailResponse)
async def get_chapter_detail(chapter_id: str, db: Session = Depends(get_db)):
    """获取章节详情（含内容）"""
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")

    # 如果数据库中没有内容，尝试从文件读取
    if not chapter.content:
        novel = db.query(Novel).filter(Novel.id == chapter.novel_id).first()
        if novel and novel.content_path:
            content = safe_read_file(novel.content_path)
            if content:
                chapter_content = chapter_splitter.get_chapter_content(content, chapter.chapter_number)
                if chapter_content:
                    chapter.content = chapter_content
                    db.commit()
                    db.refresh(chapter)

    return chapter


@router.put("/{chapter_id}", response_model=ChapterDetailResponse)
async def update_chapter(chapter_id: str, update: ChapterUpdate, db: Session = Depends(get_db)):
    """更新章节内容"""
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")

    if update.title is not None:
        chapter.title = update.title
    if update.content is not None:
        chapter.content = update.content
        chapter.word_count = len(update.content)
    if update.status is not None:
        if update.status not in ("draft", "completed", "revised"):
            raise HTTPException(status_code=400, detail="状态必须是 draft/completed/revised")
        chapter.status = update.status

    db.commit()
    db.refresh(chapter)

    # 更新小说总字数
    _update_novel_word_count(chapter.novel_id, db)

    return chapter


@router.post("/{chapter_id}/summary", response_model=ApiResponse)
async def generate_chapter_summary(chapter_id: str, db: Session = Depends(get_db)):
    """AI 生成章节摘要"""
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")

    content = chapter.content
    if not content:
        novel = db.query(Novel).filter(Novel.id == chapter.novel_id).first()
        if novel and novel.content_path:
            full_content = safe_read_file(novel.content_path)
            content = chapter_splitter.get_chapter_content(full_content, chapter.chapter_number) or ""

    if not content:
        return ApiResponse(success=False, error="章节内容为空")

    try:
        from app.agent.client import ClaudeAgentClient
        client = ClaudeAgentClient()

        prompt = f"""请为以下章节内容生成一个简洁的摘要（200字以内），概括主要事件、涉及人物和关键情节转折。

章节标题：{chapter.title or '未知'}

章节内容：
{content[:3000]}

请直接输出摘要文本，不要添加标题或格式。"""

        summary = await client.generate(prompt)
        if summary:
            chapter.summary = summary.strip()
            db.commit()
            return ApiResponse(success=True, data={"summary": summary.strip()})
        else:
            return ApiResponse(success=False, error="AI生成摘要失败")
    except Exception as e:
        logger.error(f"生成章节摘要失败: {e}")
        return ApiResponse(success=False, error=str(e))


@router.post("/reorder", response_model=ApiResponse)
async def reorder_chapters(request: ChapterReorder, db: Session = Depends(get_db)):
    """重排章节顺序"""
    for index, chapter_id in enumerate(request.chapter_ids):
        chapter = db.query(Chapter).filter(
            Chapter.id == chapter_id,
            Chapter.novel_id == request.novel_id
        ).first()
        if chapter:
            chapter.chapter_number = index + 1

    db.commit()
    return ApiResponse(success=True, data={"message": "章节顺序已更新"})


@router.put("/{chapter_id}/status", response_model=ChapterResponse)
async def update_chapter_status(chapter_id: str, status: str, db: Session = Depends(get_db)):
    """更新章节状态"""
    if status not in ("draft", "completed", "revised"):
        raise HTTPException(status_code=400, detail="状态必须是 draft/completed/revised")

    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在")

    chapter.status = status
    db.commit()
    db.refresh(chapter)
    return chapter


def _parse_and_save_chapters(novel_id: str, content: str, db: Session) -> List[Chapter]:
    """从文本解析章节并保存到数据库"""
    parsed = chapter_splitter.split(content)
    chapters = []

    for idx, (chapter_num, title, chapter_content) in enumerate(parsed):
        # 如果无法解析章节号，使用序号
        num = chapter_num if chapter_num is not None else (idx + 1)

        chapter = Chapter(
            novel_id=novel_id,
            chapter_number=num,
            title=title or f"第{num}章",
            content=chapter_content,
            word_count=len(chapter_content),
            status="draft"
        )
        db.add(chapter)
        chapters.append(chapter)

    db.commit()
    for ch in chapters:
        db.refresh(ch)

    return chapters


def _update_novel_word_count(novel_id: str, db: Session):
    """更新小说总字数"""
    total = db.query(Chapter).filter(Chapter.novel_id == novel_id).count()
    if total > 0:
        from sqlalchemy import func
        word_sum = db.query(func.sum(Chapter.word_count)).filter(
            Chapter.novel_id == novel_id
        ).scalar() or 0

        novel = db.query(Novel).filter(Novel.id == novel_id).first()
        if novel:
            novel.word_count = word_sum
            novel.chapter_count = total
            db.commit()
