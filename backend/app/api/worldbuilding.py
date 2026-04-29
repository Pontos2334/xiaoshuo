"""世界观管理 API"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
import json

from app.models.database import get_db
from app.models.models import Novel, Character, PlotNode, WorldEntity, EntityRelation
from app.models.schemas import (
    WorldEntityCreate, WorldEntityUpdate, WorldEntityResponse,
    EntityRelationCreate, EntityRelationUpdate, EntityRelationResponse,
    ConsistencyCheckResponse, ConsistencyIssue, ApiResponse,
    DeepConsistencyCheckResponse, DeepConsistencyIssue
)
from app.core.file_utils import safe_read_file
from app.core.json_utils import JSONParser

router = APIRouter()
logger = logging.getLogger(__name__)


# ========== 实体 CRUD ==========

@router.get("/entities", response_model=List[WorldEntityResponse])
async def get_entities(
    novel_id: str,
    entity_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取世界观实体列表"""
    novel = db.query(Novel).filter(Novel.id == novel_id).first()
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")

    query = db.query(WorldEntity).filter(WorldEntity.novel_id == novel_id)
    if entity_type:
        valid_types = ("location", "item", "organization", "event", "concept", "terminology")
        if entity_type not in valid_types:
            raise HTTPException(status_code=400, detail=f"类型必须是: {', '.join(valid_types)}")
        query = query.filter(WorldEntity.entity_type == entity_type)

    return query.order_by(WorldEntity.entity_type, WorldEntity.name).all()


@router.get("/entities/{entity_id}", response_model=WorldEntityResponse)
async def get_entity(entity_id: str, db: Session = Depends(get_db)):
    """获取实体详情"""
    entity = db.query(WorldEntity).filter(WorldEntity.id == entity_id).first()
    if not entity:
        raise HTTPException(status_code=404, detail="实体不存在")
    return entity


@router.post("/entities", response_model=WorldEntityResponse)
async def create_entity(entity_data: WorldEntityCreate, db: Session = Depends(get_db)):
    """创建世界观实体"""
    novel = db.query(Novel).filter(Novel.id == entity_data.novel_id).first()
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")

    entity = WorldEntity(
        novel_id=entity_data.novel_id,
        name=entity_data.name,
        entity_type=entity_data.entity_type,
        description=entity_data.description,
        attributes=entity_data.attributes or {},
        rules=entity_data.rules,
        source=entity_data.source
    )
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return entity


@router.put("/entities/{entity_id}", response_model=WorldEntityResponse)
async def update_entity(entity_id: str, update: WorldEntityUpdate, db: Session = Depends(get_db)):
    """更新实体"""
    entity = db.query(WorldEntity).filter(WorldEntity.id == entity_id).first()
    if not entity:
        raise HTTPException(status_code=404, detail="实体不存在")

    if update.name is not None:
        entity.name = update.name
    if update.entity_type is not None:
        entity.entity_type = update.entity_type
    if update.description is not None:
        entity.description = update.description
    if update.attributes is not None:
        entity.attributes = update.attributes
    if update.rules is not None:
        entity.rules = update.rules

    db.commit()
    db.refresh(entity)
    return entity


@router.delete("/entities/{entity_id}", response_model=ApiResponse)
async def delete_entity(entity_id: str, db: Session = Depends(get_db)):
    """删除实体及其关系"""
    entity = db.query(WorldEntity).filter(WorldEntity.id == entity_id).first()
    if not entity:
        raise HTTPException(status_code=404, detail="实体不存在")

    db.delete(entity)
    db.commit()
    return ApiResponse(success=True, data={"message": f"已删除实体「{entity.name}」"})


# ========== 实体关系 CRUD ==========

@router.get("/relations", response_model=List[EntityRelationResponse])
async def get_relations(novel_id: str, db: Session = Depends(get_db)):
    """获取实体关系列表"""
    relations = db.query(EntityRelation).filter(
        EntityRelation.novel_id == novel_id
    ).all()

    result = []
    for rel in relations:
        resp = EntityRelationResponse(
            id=rel.id,
            novel_id=rel.novel_id,
            source_id=rel.source_id,
            target_id=rel.target_id,
            relation_type=rel.relation_type,
            description=rel.description,
            source_name=rel.source_entity.name if rel.source_entity else None,
            target_name=rel.target_entity.name if rel.target_entity else None
        )
        result.append(resp)
    return result


@router.post("/relations", response_model=EntityRelationResponse)
async def create_relation(rel_data: EntityRelationCreate, db: Session = Depends(get_db)):
    """创建实体关系"""
    source = db.query(WorldEntity).filter(WorldEntity.id == rel_data.source_id).first()
    target = db.query(WorldEntity).filter(WorldEntity.id == rel_data.target_id).first()
    if not source or not target:
        raise HTTPException(status_code=400, detail="源实体或目标实体不存在")

    relation = EntityRelation(
        novel_id=rel_data.novel_id,
        source_id=rel_data.source_id,
        target_id=rel_data.target_id,
        relation_type=rel_data.relation_type,
        description=rel_data.description
    )
    db.add(relation)
    db.commit()
    db.refresh(relation)

    return EntityRelationResponse(
        id=relation.id,
        novel_id=relation.novel_id,
        source_id=relation.source_id,
        target_id=relation.target_id,
        relation_type=relation.relation_type,
        description=relation.description,
        source_name=source.name,
        target_name=target.name
    )


@router.put("/relations/{relation_id}", response_model=EntityRelationResponse)
async def update_relation(relation_id: str, update: EntityRelationUpdate, db: Session = Depends(get_db)):
    """更新实体关系"""
    relation = db.query(EntityRelation).filter(EntityRelation.id == relation_id).first()
    if not relation:
        raise HTTPException(status_code=404, detail="关系不存在")

    if update.relation_type is not None:
        relation.relation_type = update.relation_type
    if update.description is not None:
        relation.description = update.description

    db.commit()
    db.refresh(relation)

    return EntityRelationResponse(
        id=relation.id,
        novel_id=relation.novel_id,
        source_id=relation.source_id,
        target_id=relation.target_id,
        relation_type=relation.relation_type,
        description=relation.description,
        source_name=relation.source_entity.name if relation.source_entity else None,
        target_name=relation.target_entity.name if relation.target_entity else None
    )


@router.delete("/relations/{relation_id}", response_model=ApiResponse)
async def delete_relation(relation_id: str, db: Session = Depends(get_db)):
    """删除实体关系"""
    relation = db.query(EntityRelation).filter(EntityRelation.id == relation_id).first()
    if not relation:
        raise HTTPException(status_code=404, detail="关系不存在")

    db.delete(relation)
    db.commit()
    return ApiResponse(success=True, data={"message": "已删除关系"})


# ========== AI 功能 ==========

@router.post("/entities/extract", response_model=ApiResponse)
async def extract_entities(novel_id: str, entity_type: Optional[str] = None, db: Session = Depends(get_db)):
    """AI 从小说文本中提取世界观实体"""
    novel = db.query(Novel).filter(Novel.id == novel_id).first()
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")

    content = ""
    if novel.content_path:
        content = safe_read_file(novel.content_path)

    if not content:
        return ApiResponse(success=False, error="小说内容为空")

    # 限制文本长度，取前8000字
    text_sample = content[:8000]

    try:
        from app.agent.client import ClaudeAgentClient
        client = ClaudeAgentClient()

        type_hint = f"重点关注类型：{entity_type}" if entity_type else "所有类型（location/item/organization/event/concept/terminology）"

        prompt = f"""请从以下小说文本中提取世界观设定元素。{type_hint}

提取要求：
1. 地点(location)：场景、城市、国家、特殊区域
2. 物品(item)：法宝、武器、重要道具
3. 组织(organization)：门派、势力、团体
4. 事件(event)：历史事件、背景故事
5. 概念(concept)：功法体系、规则、魔法体系
6. 术语(terminology)：专用名词、独特概念

请以JSON格式输出，格式如下：
```json
{{
  "entities": [
    {{
      "name": "实体名称",
      "entity_type": "类型",
      "description": "详细描述",
      "attributes": {{"key": "value"}},
      "rules": "相关规则（如有）"
    }}
  ]
}}
```

小说文本：
{text_sample}"""

        response = await client.generate(prompt)
        if not response:
            return ApiResponse(success=False, error="AI生成失败")

        # 解析 JSON 响应
        entities_data = JSONParser.safe_parse_json(response)
        if not entities_data or "entities" not in entities_data:
            return ApiResponse(success=False, error="AI响应格式错误")

        created = []
        for item in entities_data["entities"]:
            entity = WorldEntity(
                novel_id=novel_id,
                name=item.get("name", ""),
                entity_type=item.get("entity_type", "concept"),
                description=item.get("description", ""),
                attributes=item.get("attributes", {}),
                rules=item.get("rules"),
                source="ai"
            )
            db.add(entity)
            created.append(entity)

        db.commit()
        for e in created:
            db.refresh(e)

        return ApiResponse(
            success=True,
            data={
                "count": len(created),
                "entities": [WorldEntityResponse.model_validate(e).model_dump() for e in created]
            }
        )
    except Exception as e:
        logger.error(f"AI提取实体失败: {e}")
        return ApiResponse(success=False, error=str(e))


@router.post("/terminology/auto", response_model=ApiResponse)
async def auto_extract_terminology(novel_id: str, db: Session = Depends(get_db)):
    """AI 自动提取术语表"""
    novel = db.query(Novel).filter(Novel.id == novel_id).first()
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")

    content = ""
    if novel.content_path:
        content = safe_read_file(novel.content_path)
    if not content:
        return ApiResponse(success=False, error="小说内容为空")

    text_sample = content[:8000]

    try:
        from app.agent.client import ClaudeAgentClient
        client = ClaudeAgentClient()

        prompt = f"""请从以下小说文本中提取所有专用术语和独特概念，生成术语表。

要求：
1. 提取小说中的专用名词、武功招式、特殊能力、种族、等级等
2. 每个术语包含名称和定义/解释
3. 按出现频率或重要性排序

请以JSON格式输出：
```json
{{
  "terms": [
    {{
      "name": "术语名称",
      "description": "定义和解释",
      "attributes": {{"分类": "类别"}}
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
        if not data or "terms" not in data:
            return ApiResponse(success=False, error="AI响应格式错误")

        created = []
        for item in data["terms"]:
            entity = WorldEntity(
                novel_id=novel_id,
                name=item.get("name", ""),
                entity_type="terminology",
                description=item.get("description", ""),
                attributes=item.get("attributes", {}),
                source="ai"
            )
            db.add(entity)
            created.append(entity)

        db.commit()
        for e in created:
            db.refresh(e)

        return ApiResponse(
            success=True,
            data={
                "count": len(created),
                "entities": [WorldEntityResponse.model_validate(e).model_dump() for e in created]
            }
        )
    except Exception as e:
        logger.error(f"自动提取术语失败: {e}")
        return ApiResponse(success=False, error=str(e))


@router.get("/timeline", response_model=ApiResponse)
async def get_timeline(novel_id: str, db: Session = Depends(get_db)):
    """获取事件时间线"""
    events = db.query(WorldEntity).filter(
        WorldEntity.novel_id == novel_id,
        WorldEntity.entity_type == "event"
    ).order_by(WorldEntity.created_at).all()

    return ApiResponse(
        success=True,
        data=[WorldEntityResponse.model_validate(e).model_dump() for e in events]
    )


# ========== 一致性检查 ==========

@router.post("/consistency/check", response_model=ConsistencyCheckResponse)
async def check_consistency(novel_id: str, db: Session = Depends(get_db)):
    """AI 一致性检查"""
    novel = db.query(Novel).filter(Novel.id == novel_id).first()
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")

    # 收集数据
    characters = db.query(Character).filter(Character.novel_id == novel_id).all()
    plots = db.query(PlotNode).filter(PlotNode.novel_id == novel_id).all()
    world_entities = db.query(WorldEntity).filter(WorldEntity.novel_id == novel_id).all()

    content = ""
    if novel.content_path:
        content = safe_read_file(novel.content_path)

    if not content:
        return ConsistencyCheckResponse(
            novel_id=novel_id,
            total_issues=0,
            issues=[ConsistencyIssue(
                type="info",
                severity="info",
                description="小说内容为空，无法进行一致性检查"
            )]
        )

    # 构建上下文
    char_descriptions = []
    for c in characters[:20]:
        info = f"- {c.name}"
        if c.basic_info:
            basic = c.basic_info if isinstance(c.basic_info, dict) else {}
            info += f"，基本信息: {json.dumps(basic, ensure_ascii=False)}"
        if c.personality:
            pers = c.personality if isinstance(c.personality, list) else []
            info += f"，性格: {', '.join(pers[:5])}"
        char_descriptions.append(info)

    plot_descriptions = []
    for p in plots[:20]:
        plot_descriptions.append(f"- 第{p.chapter}章: {p.title} - {p.summary or '无摘要'}")

    rules = []
    for e in world_entities:
        if e.rules:
            rules.append(f"- {e.name}({e.entity_type}): {e.rules}")

    text_sample = content[:6000]

    try:
        from app.agent.client import ClaudeAgentClient
        client = ClaudeAgentClient()

        prompt = f"""请检查以下小说内容的一致性，查找可能存在的矛盾和错误。

人物设定：
{chr(10).join(char_descriptions) if char_descriptions else '无人物数据'}

情节摘要：
{chr(10).join(plot_descriptions) if plot_descriptions else '无情节数据'}

世界观规则：
{chr(10).join(rules) if rules else '无规则数据'}

小说文本（部分）：
{text_sample}

请检查以下维度：
1. 人物一致性：外貌、能力、性格在不同章节是否矛盾
2. 时间线一致性：事件顺序是否合理，角色是否在不应出现时出场
3. 规则一致性：是否违反已定义的世界观规则
4. 关系一致性：人物关系是否前后矛盾

以JSON格式输出：
```json
{{
  "issues": [
    {{
      "type": "character|timeline|rule|relation",
      "severity": "error|warning|info",
      "description": "问题描述",
      "chapter_a": "相关章节1",
      "chapter_b": "相关章节2",
      "detail": "详细说明",
      "suggestion": "修改建议"
    }}
  ]
}}
```

如果没有发现问题，返回空数组。只报告确信的矛盾，不要猜测。"""

        response = await client.generate(prompt)
        if not response:
            return ConsistencyCheckResponse(
                novel_id=novel_id, total_issues=0, issues=[]
            )

        data = JSONParser.safe_parse_json(response)
        issues = []
        if data and "issues" in data:
            for item in data["issues"]:
                issues.append(ConsistencyIssue(
                    type=item.get("type", "info"),
                    severity=item.get("severity", "warning"),
                    description=item.get("description", ""),
                    chapter_a=item.get("chapter_a"),
                    chapter_b=item.get("chapter_b"),
                    detail=item.get("detail"),
                    suggestion=item.get("suggestion")
                ))

        return ConsistencyCheckResponse(
            novel_id=novel_id,
            total_issues=len(issues),
            issues=issues
        )
    except Exception as e:
        logger.error(f"一致性检查失败: {e}")
        return ConsistencyCheckResponse(
            novel_id=novel_id,
            total_issues=1,
            issues=[ConsistencyIssue(
                type="info",
                severity="info",
                description=f"一致性检查出错: {str(e)}"
            )]
        )



@router.post("/consistency/deep-check", response_model=DeepConsistencyCheckResponse)
async def deep_consistency_check(novel_id: str, db: Session = Depends(get_db)):
    """深度一致性检查 - 检测角色/时间线/战力/地理/称呼等多维度问题"""
    novel = db.query(Novel).filter(Novel.id == novel_id).first()
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")

    characters = db.query(Character).filter(Character.novel_id == novel_id).all()
    plots = db.query(PlotNode).filter(PlotNode.novel_id == novel_id).all()
    world_entities = db.query(WorldEntity).filter(WorldEntity.novel_id == novel_id).all()

    content = ""
    if novel.content_path:
        content = safe_read_file(novel.content_path)

    if not content:
        return DeepConsistencyCheckResponse(
            novel_id=novel_id, total_issues=0, checks_run=[], issues=[]
        )

    # 构建上下文
    characters_info = "\n".join([
        f"- {c.name}: {json.dumps(c.basic_info or {}, ensure_ascii=False)}" for c in characters[:30]
    ])
    plots_info = "\n".join([
        f"- 第{p.chapter}章 {p.title}: {p.summary or ''}" for p in plots[:30]
    ])
    entities_info = "\n".join([
        f"- {e.name}({e.entity_type}): {e.description or ''} 规则:{e.rules or '无'}" for e in world_entities[:30]
    ])

    try:
        from app.services.deep_consistency_checker import DeepConsistencyChecker
        checker = DeepConsistencyChecker()

        # 构建上下文信息
        characters_info = "\n".join([
            f"- {c.name}: {json.dumps(c.basic_info if isinstance(c.basic_info, dict) else {}, ensure_ascii=False)}"
            for c in characters[:20]
        ]) if characters else "无人物数据"

        plots_info = "\n".join([
            f"- 第{p.chapter}章: {p.title or ''} - {p.summary or ''}"
            for p in plots[:20]
        ]) if plots else "无情节数据"

        entities_info = "\n".join([
            f"- {e.name}({e.entity_type}): {e.description or ''} 规则:{e.rules or '无'}"
            for e in world_entities[:20]
        ]) if world_entities else "无世界观数据"

        issues_raw = await checker.check_all(
            characters_info=characters_info,
            plot_nodes_info=plots_info,
            entities_info=entities_info,
            chapters_content=content[:15000]
        )

        checks_run = ["dead_characters", "timeline", "power_system", "geography", "naming"]
        deep_issues = [
            DeepConsistencyIssue(
                type=item.get("type", "info"),
                severity=item.get("severity", "warning"),
                description=item.get("description", ""),
                chapter_a=item.get("chapter_a"),
                chapter_b=item.get("chapter_b"),
                detail=item.get("detail"),
                suggestion=item.get("suggestion")
            ) for item in issues_raw
        ]

        return DeepConsistencyCheckResponse(
            novel_id=novel_id,
            total_issues=len(deep_issues),
            checks_run=checks_run,
            issues=deep_issues
        )
    except Exception as e:
        logger.error(f"深度一致性检查失败: {e}")
        return DeepConsistencyCheckResponse(
            novel_id=novel_id,
            total_issues=1,
            checks_run=[],
            issues=[DeepConsistencyIssue(
                type="info",
                severity="info",
                description=f"深度一致性检查出错: {str(e)}"
            )]
        )
