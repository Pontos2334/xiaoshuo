"""节奏张力 API"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
import json

from app.models.database import get_db
from app.models.models import Novel, Chapter, TensionPoint
from app.models.schemas import (
    TensionPointCreate, TensionPointUpdate, TensionPointResponse, ApiResponse
)
from app.core.file_utils import safe_read_file
from app.core.json_utils import JSONParser
from app.core.text_sampler import sample_text

router = APIRouter()
logger = logging.getLogger(__name__)


# ========== CRUD ==========

@router.get("", response_model=List[TensionPointResponse])
async def get_tension_points(
    novel_id: str,
    chapter_from: Optional[int] = None,
    chapter_to: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """获取节奏张力点列表，可选按章节范围过滤"""
    novel = db.query(Novel).filter(Novel.id == novel_id).first()
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")

    query = db.query(TensionPoint).filter(TensionPoint.novel_id == novel_id)
    if chapter_from is not None:
        query = query.filter(TensionPoint.chapter_number >= chapter_from)
    if chapter_to is not None:
        query = query.filter(TensionPoint.chapter_number <= chapter_to)

    return query.order_by(TensionPoint.chapter_number).all()


@router.get("/{tension_id}", response_model=TensionPointResponse)
async def get_tension_point(tension_id: str, db: Session = Depends(get_db)):
    """获取节奏张力点详情"""
    point = db.query(TensionPoint).filter(TensionPoint.id == tension_id).first()
    if not point:
        raise HTTPException(status_code=404, detail="节奏张力点不存在")
    return point


@router.post("", response_model=TensionPointResponse)
async def create_tension_point(data: TensionPointCreate, db: Session = Depends(get_db)):
    """创建或更新节奏张力点（如果该章节已有记录则更新）"""
    novel = db.query(Novel).filter(Novel.id == data.novel_id).first()
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")

    # 检查是否已有该章节的张力记录
    existing = db.query(TensionPoint).filter(
        TensionPoint.novel_id == data.novel_id,
        TensionPoint.chapter_number == data.chapter_number
    ).first()

    if existing:
        # 更新现有记录
        existing.tension_level = data.tension_level
        existing.emotion_tags = data.emotion_tags or []
        existing.key_events_summary = data.key_events_summary
        existing.pacing_note = data.pacing_note
        existing.reader_hook_score = data.reader_hook_score
        existing.cliffhanger_score = data.cliffhanger_score
        existing.source = data.source
        db.commit()
        db.refresh(existing)
        return existing

    point = TensionPoint(
        novel_id=data.novel_id,
        chapter_number=data.chapter_number,
        tension_level=data.tension_level,
        emotion_tags=data.emotion_tags or [],
        key_events_summary=data.key_events_summary,
        pacing_note=data.pacing_note,
        reader_hook_score=data.reader_hook_score,
        cliffhanger_score=data.cliffhanger_score,
        source=data.source,
    )
    db.add(point)
    db.commit()
    db.refresh(point)
    return point


@router.delete("/{tension_id}", response_model=ApiResponse)
async def delete_tension_point(tension_id: str, db: Session = Depends(get_db)):
    """删除节奏张力点"""
    point = db.query(TensionPoint).filter(TensionPoint.id == tension_id).first()
    if not point:
        raise HTTPException(status_code=404, detail="节奏张力点不存在")

    db.delete(point)
    db.commit()
    return ApiResponse(success=True, data={"message": "已删除节奏张力点"})


# ========== AI 功能 ==========

@router.post("/analyze", response_model=ApiResponse)
async def analyze_tension(novel_id: str, db: Session = Depends(get_db)):
    """AI 分析所有章节的节奏张力"""
    novel = db.query(Novel).filter(Novel.id == novel_id).first()
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")

    content = safe_read_file(novel.content_path) if novel.content_path else ""
    if not content:
        return ApiResponse(success=False, error="小说内容为空")

    # 尝试按章节拆分
    chapters_text = ""
    try:
        from app.services.chapter_splitter import chapter_splitter
        parsed = chapter_splitter.split(content)
        chapter_parts = []
        for num, title, ch_content in parsed[:20]:
            chapter_parts.append(f"=== 第{num}章 {title} ===\n{ch_content[:1500]}")
        chapters_text = "\n\n".join(chapter_parts)
    except Exception:
        chapters_text = sample_text(content, 8000)

    if not chapters_text:
        chapters_text = sample_text(content, 8000)

    try:
        from app.agent.client import ClaudeAgentClient
        client = ClaudeAgentClient()

        prompt = f"""请分析以下小说各章节的节奏和张力。

对每一章分析：
1. 张力等级（1-10，1=平静叙述，10=高潮紧张）
2. 情绪标签（如：紧张、温馨、悲伤、愤怒、期待、恐惧、震惊等）
3. 关键事件摘要
4. 节奏评估（是否过快/过慢/适中）
5. 读者钩子得分（前3章）：评估吸引读者继续阅读的能力（1-10）
6. 悬念得分：章末悬念强度（1-10）

以JSON格式输出：
```json
{{
  "tension_points": [
    {{
      "chapter_number": 章节号,
      "tension_level": 1-10,
      "emotion_tags": ["情绪标签"],
      "key_events_summary": "关键事件摘要",
      "pacing_note": "节奏评估",
      "reader_hook_score": 1-10或null,
      "cliffhanger_score": 1-10或null
    }}
  ]
}}
```

小说章节内容：
{chapters_text}"""

        response = await client.generate(prompt)
        if not response:
            return ApiResponse(success=False, error="AI生成失败")

        data = JSONParser.safe_parse_json(response)
        if not data or "tension_points" not in data:
            return ApiResponse(success=False, error="AI响应格式错误")

        saved = []
        for item in data["tension_points"]:
            ch_num = item.get("chapter_number", 0)
            if not ch_num:
                continue

            # 检查是否已存在，存在则更新
            existing = db.query(TensionPoint).filter(
                TensionPoint.novel_id == novel_id,
                TensionPoint.chapter_number == ch_num
            ).first()

            if existing:
                existing.tension_level = item.get("tension_level", 5)
                existing.emotion_tags = item.get("emotion_tags", [])
                existing.key_events_summary = item.get("key_events_summary")
                existing.pacing_note = item.get("pacing_note")
                existing.reader_hook_score = item.get("reader_hook_score")
                existing.cliffhanger_score = item.get("cliffhanger_score")
                existing.source = "ai"
                saved.append(existing)
            else:
                point = TensionPoint(
                    novel_id=novel_id,
                    chapter_number=ch_num,
                    tension_level=item.get("tension_level", 5),
                    emotion_tags=item.get("emotion_tags", []),
                    key_events_summary=item.get("key_events_summary"),
                    pacing_note=item.get("pacing_note"),
                    reader_hook_score=item.get("reader_hook_score"),
                    cliffhanger_score=item.get("cliffhanger_score"),
                    source="ai",
                )
                db.add(point)
                saved.append(point)

        db.commit()
        for s in saved:
            db.refresh(s)

        return ApiResponse(
            success=True,
            data={
                "count": len(saved),
                "items": [TensionPointResponse.model_validate(s).model_dump() for s in saved]
            }
        )
    except Exception as e:
        logger.error(f"AI分析节奏张力失败: {e}")
        return ApiResponse(success=False, error=str(e))


@router.post("/pacing-issues", response_model=ApiResponse)
async def detect_pacing_issues(novel_id: str, db: Session = Depends(get_db)):
    """AI 检测节奏问题"""
    novel = db.query(Novel).filter(Novel.id == novel_id).first()
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")

    # 获取已有的张力数据
    tension_points = db.query(TensionPoint).filter(
        TensionPoint.novel_id == novel_id
    ).order_by(TensionPoint.chapter_number).all()

    if not tension_points:
        # 如果没有张力数据，先尝试分析
        return ApiResponse(
            success=True,
            data={"issues": [], "message": "暂无张力数据，请先执行节奏分析"}
        )

    # 构建张力曲线描述
    curve_desc = []
    for tp in tension_points:
        desc = f"第{tp.chapter_number}章: 张力={tp.tension_level}/10"
        if tp.emotion_tags:
            tags = tp.emotion_tags if isinstance(tp.emotion_tags, list) else []
            desc += f", 情绪: {', '.join(str(t) for t in tags[:5])}"
        if tp.pacing_note:
            desc += f", 节奏: {tp.pacing_note}"
        curve_desc.append(desc)

    try:
        from app.agent.client import ClaudeAgentClient
        client = ClaudeAgentClient()

        prompt = f"""请根据以下小说各章节的张力数据，检测节奏问题。

章节张力曲线：
{chr(10).join(curve_desc)}

检测以下节奏问题：
1. 高潮过密：连续多章高张力，缺少喘息空间
2. 低谷过长：连续多章低张力，可能让读者失去兴趣
3. 节奏突变：张力急剧跳升或下降（缺乏过渡）
4. 开头乏力：前3章张力过低，难以吸引读者
5. 结尾泄气：最后几章张力下降过快

以JSON格式输出：
```json
{{
  "issues": [
    {{
      "type": "high_density|low_valley|sudden_shift|weak_start|weak_ending",
      "severity": "error|warning|info",
      "chapter_range": "涉及章节范围",
      "description": "问题描述",
      "suggestion": "修改建议"
    }}
  ],
  "overall_pacing_score": 1-10,
  "pacing_summary": "整体节奏评估"
}}
```

如果没有发现明显问题，返回空数组并给出整体评分。"""

        response = await client.generate(prompt)
        if not response:
            return ApiResponse(success=False, error="AI生成失败")

        data = JSONParser.safe_parse_json(response)
        if not data:
            return ApiResponse(success=False, error="AI响应格式错误")

        return ApiResponse(
            success=True,
            data={
                "total_chapters_analyzed": len(tension_points),
                "issues": data.get("issues", []),
                "overall_pacing_score": data.get("overall_pacing_score"),
                "pacing_summary": data.get("pacing_summary"),
            }
        )
    except Exception as e:
        logger.error(f"节奏问题检测失败: {e}")
        return ApiResponse(success=False, error=str(e))


@router.post("/{chapter_number}/cliffhanger", response_model=ApiResponse)
async def suggest_cliffhanger(
    chapter_number: int,
    novel_id: str,
    db: Session = Depends(get_db)
):
    """AI 为指定章节建议悬念结尾"""
    novel = db.query(Novel).filter(Novel.id == novel_id).first()
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")

    content = safe_read_file(novel.content_path) if novel.content_path else ""
    if not content:
        return ApiResponse(success=False, error="小说内容为空")

    # 获取指定章节内容
    chapter_content = ""
    try:
        from app.services.chapter_splitter import chapter_splitter
        chapter_content = chapter_splitter.get_chapter_content(content, chapter_number) or ""
    except Exception:
        pass

    if not chapter_content:
        # 尝试从数据库获取
        chapter = db.query(Chapter).filter(
            Chapter.novel_id == novel_id,
            Chapter.chapter_number == chapter_number
        ).first()
        if chapter and chapter.content:
            chapter_content = chapter.content

    if not chapter_content:
        return ApiResponse(success=False, error=f"无法获取第{chapter_number}章内容")

    # 同时获取下一章开头（如果有的话），用于衔接
    next_chapter_content = ""
    try:
        from app.services.chapter_splitter import chapter_splitter
        next_chapter_content = chapter_splitter.get_chapter_content(content, chapter_number + 1) or ""
        next_chapter_content = next_chapter_content[:500]  # 只取开头部分
    except Exception:
        pass

    try:
        from app.agent.client import ClaudeAgentClient
        client = ClaudeAgentClient()

        next_hint = ""
        if next_chapter_content:
            next_hint = f"\n下一章开头（用于衔接参考）:\n{next_chapter_content}"

        prompt = f"""请为以下章节内容设计3种不同风格的悬念结尾（cliffhanger）。

当前第{chapter_number}章内容：
{chapter_content[:3000]}
{next_hint}

请提供以下3种类型的悬念结尾：
1. 悬念型：留下未解之谜
2. 转折型：意外反转
3. 危机型：角色陷入危机

每种结尾需要：
- 具体的结尾文字建议（50-150字）
- 悬念强度评分（1-10）
- 情绪类型标签

以JSON格式输出：
```json
{{
  "suggestions": [
    {{
      "type": "suspense|twist|crisis",
      "title": "类型标题",
      "text": "具体的结尾文字建议",
      "intensity": 1-10,
      "emotion_tags": ["情绪标签"],
      "transition_hint": "向下一章过渡的建议"
    }}
  ],
  "current_ending_analysis": "对当前结尾的简短分析"
}}
```"""

        response = await client.generate(prompt)
        if not response:
            return ApiResponse(success=False, error="AI生成失败")

        data = JSONParser.safe_parse_json(response)
        if not data or "suggestions" not in data:
            return ApiResponse(success=False, error="AI响应格式错误")

        return ApiResponse(
            success=True,
            data={
                "chapter_number": chapter_number,
                "suggestions": data["suggestions"],
                "current_ending_analysis": data.get("current_ending_analysis"),
            }
        )
    except Exception as e:
        logger.error(f"悬念建议失败: {e}")
        return ApiResponse(success=False, error=str(e))

