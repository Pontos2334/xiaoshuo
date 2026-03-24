from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
import logging

from app.models.database import get_db
from app.models.models import Character, CharacterRelation, Novel
from app.models.schemas import (
    CharacterResponse,
    CharacterCreate,
    CharacterUpdate,
    CharacterRelationResponse,
    CharacterRelationCreate,
    CharacterRelationUpdate,
    ApiResponse
)
from app.services.character_analyzer import CharacterAnalyzer
from app.core.file_utils import safe_read_file
from app.db.repository import character_repo, character_relation_repo

router = APIRouter()
logger = logging.getLogger(__name__)


# ========== 人物关系 API（放在动态路由之前）==========

@router.get("/relations", response_model=List[CharacterRelationResponse])
async def get_relations(novel_id: str, db: Session = Depends(get_db)):
    """获取人物关系列表"""
    logger.info(f"get_relations called with novel_id={novel_id}")
    try:
        relations = character_relation_repo.get_by_novel(novel_id)
        if relations:
            return relations
    except Exception as e:
        logger.warning(f"Neo4j 查询失败，回退到 SQLite: {e}")

    relations = db.query(CharacterRelation).filter(
        CharacterRelation.novel_id == novel_id
    ).all()
    return relations


@router.post("/relations/analyze", response_model=ApiResponse)
async def analyze_relations(novel_id: str, db: Session = Depends(get_db)):
    """AI分析人物关系"""
    novel = db.query(Novel).filter(Novel.id == novel_id).first()
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")

    # 获取所有人物
    characters = db.query(Character).filter(Character.novel_id == novel_id).all()
    if not characters:
        raise HTTPException(status_code=400, detail="请先分析人物")

    # 创建名称到ID的映射
    name_to_id = {c.name: c.id for c in characters}

    # 获取小说内容
    content = ""
    if novel.content_path:
        content = safe_read_file(novel.content_path)

    # 使用AI分析关系
    analyzer = CharacterAnalyzer()
    relations = await analyzer.analyze_relations(content, characters)

    # 辅助函数：通过名称或ID找到真正的人物ID
    def find_character_id(ref: str) -> str | None:
        if not ref:
            return None
        if ref in name_to_id.values():
            return ref
        if ref in name_to_id:
            return name_to_id[ref]
        for name, char_id in name_to_id.items():
            if name in ref or ref.replace('ID', '').replace('人物', '').strip() in name:
                return char_id
        return None

    # 保存到 Neo4j
    saved_count = 0
    for rel_data in relations:
        source_ref = rel_data.get("source_id", "")
        target_ref = rel_data.get("target_id", "")

        source_id = find_character_id(source_ref)
        target_id = find_character_id(target_ref)

        if not source_id or not target_id:
            logger.warning(f"跳过无效关系: {source_ref} -> {target_ref}")
            continue

        try:
            character_relation_repo.create(novel_id, source_id, target_id, rel_data)
            saved_count += 1
        except Exception as e:
            logger.error(f"保存关系到 Neo4j 失败: {e}")

        # 同时保存到 SQLite
        existing = db.query(CharacterRelation).filter(
            CharacterRelation.novel_id == novel_id,
            CharacterRelation.source_id == source_id,
            CharacterRelation.target_id == target_id
        ).first()

        if existing:
            for key, value in rel_data.items():
                if key not in ["source_id", "target_id"]:
                    setattr(existing, key, value)
        else:
            new_rel = CharacterRelation(
                novel_id=novel_id,
                source_id=source_id,
                target_id=target_id,
                relation_type=rel_data.get("relation_type", ""),
                description=rel_data.get("description", ""),
                strength=rel_data.get("strength", 5),
            )
            db.add(new_rel)

    db.commit()
    logger.info(f"保存了 {saved_count} 个新关系")

    # 返回所有关系
    all_relations = character_relation_repo.get_by_novel(novel_id)
    return ApiResponse(
        success=True,
        data=all_relations
    )


@router.put("/relations/{relation_id}", response_model=CharacterRelationResponse)
async def update_relation(
    relation_id: str,
    data: CharacterRelationUpdate,
    db: Session = Depends(get_db)
):
    """更新人物关系"""
    update_data = data.model_dump(exclude_unset=True)

    # 更新 Neo4j
    try:
        relation = character_relation_repo.update(relation_id, update_data)
        if relation:
            return relation
    except Exception as e:
        logger.warning(f"Neo4j 更新失败: {e}")

    # 回退到 SQLite
    relation = db.query(CharacterRelation).filter(CharacterRelation.id == relation_id).first()
    if not relation:
        raise HTTPException(status_code=404, detail="关系不存在")

    for key, value in update_data.items():
        setattr(relation, key, value)

    db.commit()
    db.refresh(relation)
    return relation


@router.delete("/relations/{relation_id}", response_model=ApiResponse)
async def delete_relation(relation_id: str, db: Session = Depends(get_db)):
    """删除人物关系"""
    # 删除 Neo4j
    try:
        character_relation_repo.delete(relation_id)
    except Exception as e:
        logger.warning(f"Neo4j 删除失败: {e}")

    # 删除 SQLite
    relation = db.query(CharacterRelation).filter(CharacterRelation.id == relation_id).first()
    if not relation:
        raise HTTPException(status_code=404, detail="关系不存在")

    db.delete(relation)
    db.commit()
    return ApiResponse(success=True, data={"message": "关系已删除"})


# ========== 人物 API ==========

@router.get("", response_model=List[CharacterResponse])
async def get_characters(novel_id: str, db: Session = Depends(get_db)):
    """获取指定小说的人物列表"""
    try:
        # 优先使用 Neo4j
        characters = character_repo.get_by_novel(novel_id)
        if characters:
            return characters
    except Exception as e:
        logger.warning(f"Neo4j 查询失败，回退到 SQLite: {e}")

    # 回退到 SQLite
    characters = db.query(Character).filter(Character.novel_id == novel_id).all()
    return characters


@router.post("/analyze", response_model=ApiResponse)
async def analyze_characters(novel_id: str, db: Session = Depends(get_db)):
    """AI分析小说内容，生成人物信息"""
    novel = db.query(Novel).filter(Novel.id == novel_id).first()
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")

    # 获取小说内容
    content = ""
    if novel.content_path:
        content = safe_read_file(novel.content_path)

    # 使用AI分析
    analyzer = CharacterAnalyzer()
    characters = await analyzer.analyze(content)

    # 保存到 Neo4j
    saved_characters = []
    for char_data in characters:
        try:
            char = character_repo.create(novel_id, char_data)
            if char:
                saved_characters.append(char)
        except Exception as e:
            logger.error(f"保存人物到 Neo4j 失败: {e}")

    # 同时保存到 SQLite（作为备份）
    for char_data in characters:
        existing = db.query(Character).filter(
            Character.novel_id == novel_id,
            Character.name == char_data.get("name")
        ).first()

        if existing:
            for key, value in char_data.items():
                setattr(existing, key, value)
        else:
            new_char = Character(
                novel_id=novel_id,
                **char_data
            )
            db.add(new_char)

    db.commit()

    # 返回所有人物
    all_characters = character_repo.get_by_novel(novel_id) or saved_characters
    return ApiResponse(
        success=True,
        data=all_characters
    )


@router.get("/{character_id}", response_model=CharacterResponse)
async def get_character(character_id: str, db: Session = Depends(get_db)):
    """获取人物详情"""
    try:
        character = character_repo.get_by_id(character_id)
        if character:
            return character
    except Exception as e:
        logger.warning(f"Neo4j 查询失败，回退到 SQLite: {e}")

    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="人物不存在")
    return character


@router.put("/{character_id}", response_model=CharacterResponse)
async def update_character(
    character_id: str,
    data: CharacterUpdate,
    db: Session = Depends(get_db)
):
    """更新人物信息"""
    update_data = data.model_dump(exclude_unset=True)

    # 更新 Neo4j
    try:
        character = character_repo.update(character_id, update_data)
        if character:
            return character
    except Exception as e:
        logger.warning(f"Neo4j 更新失败: {e}")

    # 回退到 SQLite
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="人物不存在")

    for key, value in update_data.items():
        setattr(character, key, value)

    db.commit()
    db.refresh(character)
    return character


@router.delete("/{character_id}", response_model=ApiResponse)
async def delete_character(character_id: str, db: Session = Depends(get_db)):
    """删除人物"""
    # 删除 Neo4j
    try:
        character_repo.delete(character_id)
    except Exception as e:
        logger.warning(f"Neo4j 删除失败: {e}")

    # 删除 SQLite
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="人物不存在")

    db.delete(character)
    db.commit()
    return ApiResponse(success=True, data={"message": "人物已删除"})
