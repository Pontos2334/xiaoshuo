"""角色成长弧线 API"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
import json

from app.models.database import get_db
from app.models.models import Novel, Character, CharacterArcPoint
from app.models.schemas import (
    CharacterArcPointCreate, CharacterArcPointUpdate, CharacterArcPointResponse,
    ApiResponse
)
from app.core.file_utils import safe_read_file
from app.core.json_utils import JSONParser

router = APIRouter()
logger = logging.getLogger(__name__)


# ========== CRUD ==========

@router.get("", response_model=List[CharacterArcPointResponse])
async def get_arc_points(
    novel_id: str,
    character_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取角色成长弧线点列表，可选按角色过滤"""
    novel = db.query(Novel).filter(Novel.id == novel_id).first()
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")

    query = db.query(CharacterArcPoint).filter(CharacterArcPoint.novel_id == novel_id)
    if character_id:
        character = db.query(Character).filter(Character.id == character_id).first()
        if not character:
            raise HTTPException(status_code=404, detail="人物不存在")
        query = query.filter(CharacterArcPoint.character_id == character_id)

    return query.order_by(CharacterArcPoint.chapter_number).all()


@router.get("/{arc_id}", response_model=CharacterArcPointResponse)
async def get_arc_point(arc_id: str, db: Session = Depends(get_db)):
    """获取成长弧线点详情"""
    arc = db.query(CharacterArcPoint).filter(CharacterArcPoint.id == arc_id).first()
    if not arc:
        raise HTTPException(status_code=404, detail="成长弧线点不存在")
    return arc


@router.post("", response_model=CharacterArcPointResponse)
async def create_arc_point(data: CharacterArcPointCreate, db: Session = Depends(get_db)):
    """创建成长弧线点"""
    novel = db.query(Novel).filter(Novel.id == data.novel_id).first()
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")

    character = db.query(Character).filter(Character.id == data.character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="人物不存在")

    arc = CharacterArcPoint(
        character_id=data.character_id,
        novel_id=data.novel_id,
        chapter_number=data.chapter_number,
        psychological_state=data.psychological_state,
        emotional_state=data.emotional_state,
        ability_description=data.ability_description,
        ability_level=data.ability_level,
        relationship_changes=data.relationship_changes or [],
        key_events=data.key_events or [],
        growth_notes=data.growth_notes,
        source=data.source,
    )
    db.add(arc)
    db.commit()
    db.refresh(arc)
    return arc


@router.put("/{arc_id}", response_model=CharacterArcPointResponse)
async def update_arc_point(
    arc_id: str,
    update: CharacterArcPointUpdate,
    db: Session = Depends(get_db)
):
    """更新成长弧线点"""
    arc = db.query(CharacterArcPoint).filter(CharacterArcPoint.id == arc_id).first()
    if not arc:
        raise HTTPException(status_code=404, detail="成长弧线点不存在")

    update_dict = update.model_dump(exclude_none=True)
    for key, value in update_dict.items():
        setattr(arc, key, value)

    db.commit()
    db.refresh(arc)
    return arc


@router.delete("/{arc_id}", response_model=ApiResponse)
async def delete_arc_point(arc_id: str, db: Session = Depends(get_db)):
    """删除成长弧线点"""
    arc = db.query(CharacterArcPoint).filter(CharacterArcPoint.id == arc_id).first()
    if not arc:
        raise HTTPException(status_code=404, detail="成长弧线点不存在")

    db.delete(arc)
    db.commit()
    return ApiResponse(success=True, data={"message": "已删除成长弧线点"})


# ========== AI 功能 ==========

@router.post("/extract", response_model=ApiResponse)
async def extract_arc_points(
    novel_id: str,
    character_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """AI 从小说文本中提取角色成长弧线点"""
    novel = db.query(Novel).filter(Novel.id == novel_id).first()
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")

    content = safe_read_file(novel.content_path) if novel.content_path else ""
    if not content:
        return ApiResponse(success=False, error="小说内容为空")

    # 确定要分析的人物
    if character_id:
        characters = [db.query(Character).filter(Character.id == character_id).first()]
        if not characters[0]:
            raise HTTPException(status_code=404, detail="人物不存在")
    else:
        characters = db.query(Character).filter(Character.novel_id == novel_id).all()

    if not characters:
        return ApiResponse(success=False, error="没有可分析的人物")

    text_sample = content[:8000]

    try:
        from app.agent.client import ClaudeAgentClient
        client = ClaudeAgentClient()

        # 构建人物描述
        char_descriptions = []
        for c in characters[:10]:
            desc = f"- {c.name}"
            if c.personality:
                pers = c.personality if isinstance(c.personality, list) else []
                desc += f"，性格: {', '.join(str(p) for p in pers[:5])}"
            if c.abilities:
                abil = c.abilities if isinstance(c.abilities, list) else []
                desc += f"，能力: {', '.join(str(a) for a in abil[:5])}"
            char_descriptions.append(desc)

        prompt = f"""请从以下小说文本中提取角色的成长变化轨迹。

分析的人物：
{chr(10).join(char_descriptions)}

对于每个角色，按章节追踪其变化：
1. 心理状态变化（信念、价值观、世界观）
2. 情感状态变化（人际关系、感情）
3. 能力变化（技能提升、力量增长）
4. 关键事件（触发变化的转折点）

请以JSON格式输出：
```json
{{
  "arc_points": [
    {{
      "character_name": "人物名",
      "chapter_number": 章节号,
      "psychological_state": "心理状态描述",
      "emotional_state": "情感状态描述",
      "ability_description": "能力描述",
      "ability_level": 能力等级1-10,
      "relationship_changes": [{{"target": "其他人物", "change": "变化描述"}}],
      "key_events": ["关键事件1"],
      "growth_notes": "成长总结"
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
        if not data or "arc_points" not in data:
            return ApiResponse(success=False, error="AI响应格式错误")

        # 构建人物名->ID映射
        char_name_map = {c.name: c.id for c in characters}
        # 也考虑别名
        for c in characters:
            if c.aliases:
                aliases = c.aliases if isinstance(c.aliases, list) else []
                for alias in aliases:
                    char_name_map[alias] = c.id

        saved = []
        skipped = []
        for item in data["arc_points"]:
            char_name = item.get("character_name", "")
            cid = char_name_map.get(char_name)
            if not cid:
                skipped.append(char_name)
                continue

            arc = CharacterArcPoint(
                character_id=cid,
                novel_id=novel_id,
                chapter_number=item.get("chapter_number", 1),
                psychological_state=item.get("psychological_state"),
                emotional_state=item.get("emotional_state"),
                ability_description=item.get("ability_description"),
                ability_level=item.get("ability_level"),
                relationship_changes=item.get("relationship_changes", []),
                key_events=item.get("key_events", []),
                growth_notes=item.get("growth_notes"),
                source="ai",
            )
            db.add(arc)
            saved.append(arc)

        db.commit()
        for s in saved:
            db.refresh(s)

        result = {
            "count": len(saved),
            "items": [CharacterArcPointResponse.model_validate(s).model_dump() for s in saved]
        }
        if skipped:
            result["skipped_characters"] = skipped

        return ApiResponse(success=True, data=result)
    except Exception as e:
        logger.error(f"AI提取成长弧线失败: {e}")
        return ApiResponse(success=False, error=str(e))


@router.post("/inconsistencies", response_model=ApiResponse)
async def detect_arc_inconsistencies(
    novel_id: str,
    character_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """AI 检测角色成长弧线中的不一致之处"""
    novel = db.query(Novel).filter(Novel.id == novel_id).first()
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")

    # 获取成长弧线数据
    query = db.query(CharacterArcPoint).filter(CharacterArcPoint.novel_id == novel_id)
    if character_id:
        query = query.filter(CharacterArcPoint.character_id == character_id)

    arc_points = query.order_by(CharacterArcPoint.chapter_number).all()
    if not arc_points:
        return ApiResponse(success=True, data={"inconsistencies": [], "message": "没有成长弧线数据可供检查"})

    # 按人物分组
    char_ids = set(ap.character_id for ap in arc_points)
    characters = db.query(Character).filter(Character.id.in_(char_ids)).all()
    char_map = {c.id: c.name for c in characters}

    # 构建弧线描述
    arc_descriptions = []
    for cid in char_ids:
        name = char_map.get(cid, "未知人物")
        points = sorted([ap for ap in arc_points if ap.character_id == cid], key=lambda x: x.chapter_number)
        for p in points:
            desc = (
                f"- {name} 第{p.chapter_number}章: "
                f"心理={p.psychological_state or '未知'}, "
                f"情感={p.emotional_state or '未知'}, "
                f"能力={p.ability_description or '未知'}(等级{p.ability_level or '?'})"
            )
            if p.key_events:
                events = p.key_events if isinstance(p.key_events, list) else []
                desc += f", 关键事件: {'; '.join(str(e) for e in events[:3])}"
            arc_descriptions.append(desc)

    try:
        from app.agent.client import ClaudeAgentClient
        client = ClaudeAgentClient()

        prompt = f"""请检查以下角色成长弧线数据中是否存在不一致之处。

角色成长弧线：
{chr(10).join(arc_descriptions)}

检查维度：
1. 能力倒退：角色能力突然下降（没有合理解释）
2. 性格突变：心理/情感状态跳跃性变化，缺乏过渡
3. 关系矛盾：人物关系变化前后矛盾
4. 成长逻辑：成长轨迹是否合理连贯

以JSON格式输出：
```json
{{
  "inconsistencies": [
    {{
      "character_name": "人物名",
      "type": "ability_regression|personality_shift|relationship_contradiction|growth_logic",
      "description": "不一致描述",
      "chapter_range": "涉及章节",
      "severity": "error|warning|info",
      "suggestion": "修改建议"
    }}
  ]
}}
```

如果没有发现不一致，返回空数组。"""

        response = await client.generate(prompt)
        if not response:
            return ApiResponse(success=False, error="AI生成失败")

        data = JSONParser.safe_parse_json(response)
        inconsistencies = data.get("inconsistencies", []) if data else []

        return ApiResponse(
            success=True,
            data={
                "total_arc_points": len(arc_points),
                "characters_checked": len(char_ids),
                "inconsistencies": inconsistencies
            }
        )
    except Exception as e:
        logger.error(f"成长弧线一致性检查失败: {e}")
        return ApiResponse(success=False, error=str(e))


@router.get("/growth-curve", response_model=ApiResponse)
async def get_growth_curve(character_id: str, db: Session = Depends(get_db)):
    """获取角色成长曲线（纯计算，不调用AI）"""
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="人物不存在")

    arc_points = db.query(CharacterArcPoint).filter(
        CharacterArcPoint.character_id == character_id
    ).order_by(CharacterArcPoint.chapter_number).all()

    if not arc_points:
        return ApiResponse(
            success=True,
            data={"character_id": character_id, "curve": [], "message": "暂无成长数据"}
        )

    # 构建成长曲线数据点
    curve = []
    for ap in arc_points:
        point = {
            "chapter_number": ap.chapter_number,
            "ability_level": ap.ability_level,
            "psychological_state": ap.psychological_state,
            "emotional_state": ap.emotional_state,
            "key_events": ap.key_events if isinstance(ap.key_events, list) else [],
        }
        curve.append(point)

    # 计算趋势
    ability_levels = [p.ability_level for p in arc_points if p.ability_level is not None]
    trend = "stable"
    if len(ability_levels) >= 2:
        first_half = ability_levels[:len(ability_levels) // 2]
        second_half = ability_levels[len(ability_levels) // 2:]
        avg_first = sum(first_half) / len(first_half) if first_half else 0
        avg_second = sum(second_half) / len(second_half) if second_half else 0
        if avg_second > avg_first + 0.5:
            trend = "growing"
        elif avg_second < avg_first - 0.5:
            trend = "declining"

    return ApiResponse(
        success=True,
        data={
            "character_id": character_id,
            "character_name": character.name,
            "curve": curve,
            "total_points": len(curve),
            "trend": trend,
            "ability_range": {
                "min": min(ability_levels) if ability_levels else None,
                "max": max(ability_levels) if ability_levels else None,
                "current": ability_levels[-1] if ability_levels else None,
            }
        }
    )

