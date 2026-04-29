"""伏笔追踪 API"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
import json

from app.models.database import get_db
from app.models.models import Novel, Chapter, Foreshadow
from app.models.schemas import (
    ForeshadowCreate, ForeshadowUpdate, ForeshadowResponse, ApiResponse
)
from app.core.file_utils import safe_read_file
from app.core.json_utils import JSONParser

router = APIRouter()
logger = logging.getLogger(__name__)


# ========== CRUD ==========

@router.get("", response_model=List[ForeshadowResponse])
async def get_foreshadows(
    novel_id: str,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取伏笔列表，可选按状态过滤"""
    novel = db.query(Novel).filter(Novel.id == novel_id).first()
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")

    query = db.query(Foreshadow).filter(Foreshadow.novel_id == novel_id)
    if status:
        valid_statuses = ("planted", "partially_revealed", "resolved", "abandoned")
        if status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"状态必须是: {', '.join(valid_statuses)}")
        query = query.filter(Foreshadow.status == status)

    return query.order_by(Foreshadow.plant_chapter).all()


@router.get("/{foreshadow_id}", response_model=ForeshadowResponse)
async def get_foreshadow(foreshadow_id: str, db: Session = Depends(get_db)):
    """获取伏笔详情"""
    foreshadow = db.query(Foreshadow).filter(Foreshadow.id == foreshadow_id).first()
    if not foreshadow:
        raise HTTPException(status_code=404, detail="伏笔不存在")
    return foreshadow


@router.post("", response_model=ForeshadowResponse)
async def create_foreshadow(data: ForeshadowCreate, db: Session = Depends(get_db)):
    """创建伏笔"""
    novel = db.query(Novel).filter(Novel.id == data.novel_id).first()
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")

    foreshadow = Foreshadow(
        novel_id=data.novel_id,
        title=data.title,
        description=data.description,
        plant_chapter=data.plant_chapter,
        plant_description=data.plant_description,
        status=data.status,
        resolve_chapter=data.resolve_chapter,
        resolve_description=data.resolve_description,
        related_characters=data.related_characters or [],
        related_plots=data.related_plots or [],
        importance=data.importance,
        source=data.source,
    )
    db.add(foreshadow)
    db.commit()
    db.refresh(foreshadow)
    return foreshadow


@router.put("/{foreshadow_id}", response_model=ForeshadowResponse)
async def update_foreshadow(
    foreshadow_id: str,
    update: ForeshadowUpdate,
    db: Session = Depends(get_db)
):
    """更新伏笔"""
    foreshadow = db.query(Foreshadow).filter(Foreshadow.id == foreshadow_id).first()
    if not foreshadow:
        raise HTTPException(status_code=404, detail="伏笔不存在")

    update_dict = update.model_dump(exclude_none=True)
    for key, value in update_dict.items():
        setattr(foreshadow, key, value)

    db.commit()
    db.refresh(foreshadow)
    return foreshadow


@router.delete("/{foreshadow_id}", response_model=ApiResponse)
async def delete_foreshadow(foreshadow_id: str, db: Session = Depends(get_db)):
    """删除伏笔"""
    foreshadow = db.query(Foreshadow).filter(Foreshadow.id == foreshadow_id).first()
    if not foreshadow:
        raise HTTPException(status_code=404, detail="伏笔不存在")

    db.delete(foreshadow)
    db.commit()
    return ApiResponse(success=True, data={"message": f"已删除伏笔「{foreshadow.title}」"})


# ========== AI 功能 ==========

@router.post("/extract", response_model=ApiResponse)
async def extract_foreshadows(novel_id: str, db: Session = Depends(get_db)):
    """AI 从小说文本中提取伏笔"""
    novel = db.query(Novel).filter(Novel.id == novel_id).first()
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")

    content = safe_read_file(novel.content_path) if novel.content_path else ""
    if not content:
        return ApiResponse(success=False, error="小说内容为空")

    # 构建章节映射
    chapters = db.query(Chapter).filter(
        Chapter.novel_id == novel_id
    ).order_by(Chapter.chapter_number).all()

    chapter_map = {}
    if chapters:
        for ch in chapters:
            chapter_map[ch.chapter_number] = ch.title or f"第{ch.chapter_number}章"
    else:
        # 如果数据库中没有章节，尝试从文件解析
        try:
            from app.services.chapter_splitter import chapter_splitter
            parsed = chapter_splitter.split(content)
            for idx, (num, title, _) in enumerate(parsed):
                ch_num = num if num is not None else (idx + 1)
                chapter_map[ch_num] = title or f"第{ch_num}章"
        except Exception:
            pass

    # 按章节拆分内容，限制文本长度
    text_sample = content[:8000]

    try:
        from app.agent.client import ClaudeAgentClient
        client = ClaudeAgentClient()

        chapter_info = ""
        if chapter_map:
            lines = [f"  第{num}章: {name}" for num, name in sorted(chapter_map.items())]
            chapter_info = "已知章节:\n" + "\n".join(lines[:30])

        prompt = f"""请从以下小说文本中提取所有伏笔（foreshadowing）线索。

提取要求：
1. 找出所有埋下的伏笔、暗示和悬念线索
2. 每个伏笔需记录：标题、描述、出现在第几章（plant_chapter）、涉及的人物
3. 判断伏笔的重要性（1-10）
4. 如果伏笔已被回收，记录回收章节和描述

{chapter_info}

请以JSON格式输出：
```json
{{
  "foreshadows": [
    {{
      "title": "伏笔标题",
      "description": "伏笔详细描述",
      "plant_chapter": 章节号,
      "plant_description": "埋伏笔的原文描述",
      "status": "planted|partially_revealed|resolved|abandoned",
      "resolve_chapter": 回收章节号或null,
      "resolve_description": "回收描述或null",
      "related_characters": ["人物名"],
      "related_plots": ["相关情节"],
      "importance": 重要性1-10
    }}
  ]
}}
```

小说文本：
{text_sample}"""

        response = await client.generate(prompt)
        if not response:
            return ApiResponse(success=False, error="AI生成失败")

        data = JSONParser.safe_parse_json(response)
        if not data or "foreshadows" not in data:
            return ApiResponse(success=False, error="AI响应格式错误")

        saved = []
        for item in data["foreshadows"]:
            foreshadow = Foreshadow(
                novel_id=novel_id,
                title=item.get("title", "未命名伏笔"),
                description=item.get("description"),
                plant_chapter=item.get("plant_chapter", 1),
                plant_description=item.get("plant_description"),
                status=item.get("status", "planted"),
                resolve_chapter=item.get("resolve_chapter"),
                resolve_description=item.get("resolve_description"),
                related_characters=item.get("related_characters", []),
                related_plots=item.get("related_plots", []),
                importance=item.get("importance", 5),
                source="ai",
            )
            db.add(foreshadow)
            saved.append(foreshadow)

        db.commit()
        for s in saved:
            db.refresh(s)

        return ApiResponse(
            success=True,
            data={
                "count": len(saved),
                "items": [ForeshadowResponse.model_validate(s).model_dump() for s in saved]
            }
        )
    except Exception as e:
        logger.error(f"AI提取伏笔失败: {e}")
        return ApiResponse(success=False, error=str(e))


@router.post("/check-resolution", response_model=ApiResponse)
async def check_foreshadow_resolution(novel_id: str, db: Session = Depends(get_db)):
    """AI 检查已埋下的伏笔是否已被回收"""
    novel = db.query(Novel).filter(Novel.id == novel_id).first()
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")

    # 获取所有未回收的伏笔
    planted = db.query(Foreshadow).filter(
        Foreshadow.novel_id == novel_id,
        Foreshadow.status.in_(["planted", "partially_revealed"])
    ).all()

    if not planted:
        return ApiResponse(success=True, data={"message": "没有待回收的伏笔", "results": []})

    content = safe_read_file(novel.content_path) if novel.content_path else ""
    if not content:
        return ApiResponse(success=False, error="小说内容为空")

    # 构建伏笔列表上下文
    foreshadow_list = []
    for f in planted:
        foreshadow_list.append(
            f"- ID: {f.id}, 标题: {f.title}, 埋设于第{f.plant_chapter}章, "
            f"状态: {f.status}, 描述: {f.description or '无'}"
        )

    text_sample = content[:8000]

    try:
        from app.agent.client import ClaudeAgentClient
        client = ClaudeAgentClient()

        prompt = f"""请检查以下伏笔是否已在小说文本中被回收或解决。

待检查的伏笔：
{chr(10).join(foreshadow_list)}

小说文本：
{text_sample}

请以JSON格式输出每个伏笔的检查结果：
```json
{{
  "results": [
    {{
      "foreshadow_id": "伏笔ID",
      "status": "planted|partially_revealed|resolved|abandoned",
      "evidence": "回收证据描述（如已回收）",
      "resolve_chapter": 回收章节号或null,
      "confidence": 0.0-1.0
    }}
  ]
}}
```"""

        response = await client.generate(prompt)
        if not response:
            return ApiResponse(success=False, error="AI生成失败")

        data = JSONParser.safe_parse_json(response)
        if not data or "results" not in data:
            return ApiResponse(success=False, error="AI响应格式错误")

        updated = []
        for item in data["results"]:
            foreshadow = db.query(Foreshadow).filter(Foreshadow.id == item.get("foreshadow_id")).first()
            if foreshadow and item.get("confidence", 0) >= 0.7:
                new_status = item.get("status", foreshadow.status)
                if new_status != foreshadow.status:
                    foreshadow.status = new_status
                if item.get("resolve_chapter"):
                    foreshadow.resolve_chapter = item["resolve_chapter"]
                if item.get("evidence"):
                    foreshadow.resolve_description = item["evidence"]
                updated.append(foreshadow)

        db.commit()
        for u in updated:
            db.refresh(u)

        return ApiResponse(
            success=True,
            data={
                "checked": len(planted),
                "updated": len(updated),
                "results": [
                    ForeshadowResponse.model_validate(u).model_dump() for u in updated
                ]
            }
        )
    except Exception as e:
        logger.error(f"伏笔回收检查失败: {e}")
        return ApiResponse(success=False, error=str(e))


@router.post("/{foreshadow_id}/suggest-resolution", response_model=ApiResponse)
async def suggest_foreshadow_resolution(
    foreshadow_id: str,
    db: Session = Depends(get_db)
):
    """AI 建议如何回收伏笔"""
    foreshadow = db.query(Foreshadow).filter(Foreshadow.id == foreshadow_id).first()
    if not foreshadow:
        raise HTTPException(status_code=404, detail="伏笔不存在")

    novel = db.query(Novel).filter(Novel.id == foreshadow.novel_id).first()
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")

    content = safe_read_file(novel.content_path) if novel.content_path else ""
    text_sample = content[:6000] if content else ""

    # 获取相关人物信息
    characters_str = ""
    if foreshadow.related_characters:
        characters_str = f"涉及人物: {', '.join(foreshadow.related_characters)}"

    try:
        from app.agent.client import ClaudeAgentClient
        client = ClaudeAgentClient()

        prompt = f"""请为以下小说伏笔提供回收（解决）建议。

伏笔标题: {foreshadow.title}
伏笔描述: {foreshadow.description or '无'}
埋设章节: 第{foreshadow.plant_chapter}章
埋设描述: {foreshadow.plant_description or '无'}
当前状态: {foreshadow.status}
重要性: {foreshadow.importance}/10
{characters_str}

{"小说文本（部分）:" + chr(10) + text_sample if text_sample else "（无小说文本参考）"}

请提供3种不同的回收方案，每种方案包含：
1. 方案标题
2. 回收方式描述（具体情节建议）
3. 建议回收章节范围
4. 情感效果（悬念/反转/温馨/震撼等）

以JSON格式输出：
```json
{{
  "suggestions": [
    {{
      "title": "方案标题",
      "description": "具体描述",
      "suggested_chapter_range": "第X-Y章",
      "emotional_effect": "情感效果",
      "difficulty": "简单/中等/困难"
    }}
  ]
}}
```"""

        response = await client.generate(prompt)
        if not response:
            return ApiResponse(success=False, error="AI生成失败")

        data = JSONParser.safe_parse_json(response)
        if not data or "suggestions" not in data:
            return ApiResponse(success=False, error="AI响应格式错误")

        return ApiResponse(success=True, data=data)
    except Exception as e:
        logger.error(f"伏笔回收建议失败: {e}")
        return ApiResponse(success=False, error=str(e))


@router.get("/alerts", response_model=ApiResponse)
async def get_foreshadow_alerts(
    novel_id: str,
    threshold: int = 50,
    db: Session = Depends(get_db)
):
    """获取逾期未回收的伏笔告警（超过一定章节比例仍未回收）"""
    novel = db.query(Novel).filter(Novel.id == novel_id).first()
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")

    # 获取小说最大章节号
    max_chapter = novel.chapter_count or 0
    if max_chapter == 0:
        chapters = db.query(Chapter).filter(Chapter.novel_id == novel_id).all()
        if chapters:
            max_chapter = max(ch.chapter_number for ch in chapters)

    if max_chapter == 0:
        return ApiResponse(success=True, data={"alerts": [], "total_planted": 0})

    # 查找所有未回收的伏笔
    planted = db.query(Foreshadow).filter(
        Foreshadow.novel_id == novel_id,
        Foreshadow.status.in_(["planted", "partially_revealed"])
    ).order_by(Foreshadow.plant_chapter).all()

    alerts = []
    for f in planted:
        # 计算伏笔已跨越的章节占比
        chapters_elapsed = max_chapter - f.plant_chapter
        if max_chapter > 0:
            progress_ratio = int((chapters_elapsed / max_chapter) * 100)
        else:
            progress_ratio = 0

        if progress_ratio >= threshold:
            alerts.append({
                "foreshadow": ForeshadowResponse.model_validate(f).model_dump(),
                "chapters_elapsed": chapters_elapsed,
                "progress_ratio": progress_ratio,
                "severity": "high" if progress_ratio >= 80 else "medium" if progress_ratio >= 60 else "low",
                "message": f"伏笔「{f.title}」已跨越{chapters_elapsed}章（占全书{progress_ratio}%），建议尽快回收",
            })

    return ApiResponse(
        success=True,
        data={
            "alerts": alerts,
            "total_planted": len(planted),
            "max_chapter": max_chapter,
            "threshold": threshold,
        }
    )

