from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from fastapi import Depends
import os
from typing import List
from pydantic import BaseModel
import uuid
import tempfile
import shutil

from app.models.database import get_db
from app.models.models import Novel
from app.models.schemas import NovelResponse, NovelCreate, ApiResponse

router = APIRouter()


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


@router.get("/novels/{novel_id}", response_model=ApiResponse)
async def get_novel_content(novel_id: str, db: Session = Depends(get_db)):
    """获取小说内容"""
    novel = db.query(Novel).filter(Novel.id == novel_id).first()
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")

    content = ""
    if novel.content_path and os.path.exists(novel.content_path):
        with open(novel.content_path, "r", encoding="utf-8") as f:
            content = f.read()

    outline = ""
    if novel.outline_path and os.path.exists(novel.outline_path):
        with open(novel.outline_path, "r", encoding="utf-8") as f:
            outline = f.read()

    return ApiResponse(
        success=True,
        data={
            "novel": NovelResponse.model_validate(novel).model_dump(),
            "content": content,
            "outline": outline
        }
    )


@router.post("/scan", response_model=ApiResponse)
async def scan_folder(path: str, db: Session = Depends(get_db)):
    """扫描指定文件夹，查找小说文件"""
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
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    word_count = len(content)
                    # 简单估算章节数
                    chapter_count = content.count("第") if "第" in content else 1

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
    with open(novel_path, "w", encoding="utf-8") as f:
        f.write(all_content.strip())

    # 检查是否已存在
    existing = db.query(Novel).filter(Novel.path == novel_path).first()
    if existing:
        return ApiResponse(
            success=True,
            data=[NovelResponse.model_validate(existing)]
        )

    # 估算章节数
    chapter_count = all_content.count("第") if "第" in all_content else len(request.files)

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

    return ApiResponse(
        success=True,
        data=[NovelResponse.model_validate(new_novel)]
    )
