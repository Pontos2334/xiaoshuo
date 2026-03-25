from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import logging
import re

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
from app.services.chapter_splitter import chapter_splitter
from app.core.file_utils import safe_read_file
from app.db.repository import character_repo, character_relation_repo

router = APIRouter()
logger = logging.getLogger(__name__)


# ========== 人物关系 API（放在动态路由之前）==========

@router.get("/relations", response_model=List[CharacterRelationResponse])
async def get_relations(novel_id: str, db: Session = Depends(get_db)):
    """获取人物关系列表"""
    logger.info(f"get_relations called with novel_id={novel_id}")

    # 尝试从 Neo4j 获取
    try:
        relations = character_relation_repo.get_by_novel(novel_id)
        if relations:
            logger.info(f"从 Neo4j 获取到 {len(relations)} 个关系")
            return relations
        logger.info("Neo4j 中没有关系数据")
    except Exception as e:
        logger.warning(f"Neo4j 查询失败，回退到 SQLite: {e}")

    # 从 SQLite 获取
    relations = db.query(CharacterRelation).filter(
        CharacterRelation.novel_id == novel_id
    ).all()
    logger.info(f"从 SQLite 获取到 {len(relations)} 个关系")
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

    # Saga 模式：记录已写入的数据，用于回滚
    saved_neo4j_ids: List[str] = []
    saved_sqlite_ids: List[str] = []

    try:
        # Step 1: 保存到 Neo4j
        for rel_data in relations:
            source_ref = rel_data.get("source_id", "")
            target_ref = rel_data.get("target_id", "")

            source_id = find_character_id(source_ref)
            target_id = find_character_id(target_ref)

            if not source_id or not target_id:
                logger.warning(f"跳过无效关系: {source_ref} -> {target_ref}")
                continue

            try:
                rel = character_relation_repo.create(novel_id, source_id, target_id, rel_data)
                if rel:
                    saved_neo4j_ids.append(rel.get("id"))
            except Exception as e:
                logger.error(f"保存关系到 Neo4j 失败: {e}")

        # Step 2: 保存到 SQLite
        for rel_data in relations:
            source_ref = rel_data.get("source_id", "")
            target_ref = rel_data.get("target_id", "")

            source_id = find_character_id(source_ref)
            target_id = find_character_id(target_ref)

            if not source_id or not target_id:
                continue

            existing = db.query(CharacterRelation).filter(
                CharacterRelation.novel_id == novel_id,
                CharacterRelation.source_id == source_id,
                CharacterRelation.target_id == target_id
            ).first()

            if existing:
                for key, value in rel_data.items():
                    if key not in ["source_id", "target_id"]:
                        setattr(existing, key, value)
                saved_sqlite_ids.append(existing.id)
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
                db.flush()
                saved_sqlite_ids.append(new_rel.id)

        # 两边都成功，提交事务
        db.commit()
        logger.info(f"成功保存 {len(saved_neo4j_ids)} 个 Neo4j 关系, {len(saved_sqlite_ids)} 个 SQLite 关系")

    except Exception as e:
        logger.error(f"保存关系失败，开始回滚: {e}")

        # 回滚 Neo4j
        for rel_id in saved_neo4j_ids:
            try:
                character_relation_repo.delete(rel_id)
            except Exception as rollback_error:
                logger.error(f"回滚 Neo4j 关系失败 {rel_id}: {rollback_error}")

        # SQLite 自动回滚
        db.rollback()

        raise HTTPException(status_code=500, detail=f"保存关系失败: {str(e)}")

    # 返回所有关系
    try:
        all_relations = character_relation_repo.get_by_novel(novel_id)
        if not all_relations:
            # Neo4j 没有数据，从 SQLite 获取
            all_relations = db.query(CharacterRelation).filter(
                CharacterRelation.novel_id == novel_id
            ).all()
            logger.info(f"从 SQLite 获取到 {len(all_relations)} 个关系用于返回")
    except Exception as e:
        logger.warning(f"从 Neo4j 获取关系失败: {e}，回退到 SQLite")
        all_relations = db.query(CharacterRelation).filter(
            CharacterRelation.novel_id == novel_id
        ).all()

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
async def analyze_characters(
    novel_id: str,
    mode: str = Query('full', description="分析模式: full(全量) | incremental(增量)"),
    db: Session = Depends(get_db)
):
    """
    AI分析小说内容，生成人物信息

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
    if novel.content_path:
        content = safe_read_file(novel.content_path)

    if not content:
        raise HTTPException(status_code=400, detail="小说内容为空")

    # 获取当前分析版本
    current_version = (novel.analysis_version or 0) + 1

    analyzer = CharacterAnalyzer()

    # 根据模式选择分析方法
    if mode == 'incremental' and novel.last_analyzed_chapter and novel.last_analyzed_chapter > 0:
        # 增量分析模式
        logger.info(f"增量分析模式: 从第 {novel.last_analyzed_chapter + 1} 章开始")

        # 获取现有人物数据
        existing_characters = db.query(Character).filter(
            Character.novel_id == novel_id
        ).all()

        # 转换为字典列表
        existing_chars_data = []
        for c in existing_characters:
            existing_chars_data.append({
                'id': c.id,
                'name': c.name,
                'aliases': c.aliases or [],
                'basic_info': c.basic_info or {},
                'personality': c.personality or [],
                'abilities': c.abilities or [],
                'story_summary': c.story_summary,
                'first_appear': c.first_appear,
                'source': c.source or 'ai',
                'ai_version': c.ai_version or 1,
            })

        # 增量分析
        characters = await analyzer.analyze_incremental(
            content,
            existing_chars_data,
            novel.last_analyzed_chapter + 1,  # 从下一章开始
            current_version
        )

        # 计算新的最大章节号
        new_max_chapter = chapter_splitter.get_max_chapter_num(content)

    else:
        # 全量分析模式
        logger.info("全量分析模式")

        # 全量分析前，先删除该小说的所有旧人物数据
        logger.info(f"删除小说 {novel_id} 的旧人物数据...")

        # 删除 Neo4j 中的人物
        try:
            old_neo4j_chars = character_repo.get_by_novel(novel_id) or []
            for old_char in old_neo4j_chars:
                try:
                    character_repo.delete(old_char.get('id'))
                except Exception as e:
                    logger.warning(f"删除 Neo4j 人物失败: {e}")
            logger.info(f"已删除 {len(old_neo4j_chars)} 个 Neo4j 人物")
        except Exception as e:
            logger.warning(f"获取/删除 Neo4j 人物失败: {e}")

        # 删除 SQLite 中的人物关系
        db.query(CharacterRelation).filter(CharacterRelation.novel_id == novel_id).delete()

        # 删除 SQLite 中的人物
        deleted_sqlite = db.query(Character).filter(Character.novel_id == novel_id).delete()
        db.commit()
        logger.info(f"已删除 {deleted_sqlite} 个 SQLite 人物")

        try:
            raw_characters = await analyzer.analyze(content)
            logger.info(f"AI 分析完成，返回 {len(raw_characters)} 个人物")
        except Exception as e:
            logger.error(f"AI 分析失败: {type(e).__name__}: {e}")
            raise HTTPException(status_code=500, detail=f"AI 分析失败: {str(e)}")

        # 对 AI 返回的人物进行去重合并
        characters = []
        seen_names = {}
        try:
            for char in raw_characters:
                name = char.get('name', '')
                if not name:
                    continue

                # 标准化名字（去除空格和常见后缀）
                normalized_name = re.sub(r'\s+', '', name.strip())
                # 去除常见后缀如（师兄）、（师傅）等
                normalized_name = re.sub(r'[（(][^）)]*[）)]', '', normalized_name).strip()

                if normalized_name in seen_names:
                    # 合并到已存在的人物
                    existing = seen_names[normalized_name]
                    # 合并别名
                    if char.get('aliases'):
                        existing_aliases = existing.get('aliases', [])
                        for alias in char['aliases']:
                            if alias not in existing_aliases:
                                existing_aliases.append(alias)
                        existing['aliases'] = existing_aliases
                    # 合并性格
                    if char.get('personality'):
                        existing_personality = existing.get('personality', [])
                        for p in char['personality']:
                            if p not in existing_personality:
                                existing_personality.append(p)
                        existing['personality'] = existing_personality
                    # 合并能力
                    if char.get('abilities'):
                        existing_abilities = existing.get('abilities', [])
                        for a in char['abilities']:
                            if a not in existing_abilities:
                                existing_abilities.append(a)
                        existing['abilities'] = existing_abilities
                else:
                    # 新人物
                    char['source'] = 'ai'
                    char['ai_version'] = current_version
                    characters.append(char)
                    seen_names[normalized_name] = char

            logger.info(f"去重合并后剩余 {len(characters)} 个人物")
        except Exception as e:
            logger.error(f"人物去重合并失败: {type(e).__name__}: {e}")
            raise HTTPException(status_code=500, detail=f"人物去重合并失败: {str(e)}")

        # 计算最大章节号
        try:
            new_max_chapter = chapter_splitter.get_max_chapter_num(content)
            logger.info(f"最大章节号: {new_max_chapter}")
        except Exception as e:
            logger.warning(f"计算章节号失败: {e}")
            new_max_chapter = 0

    # Saga 模式：记录已写入的数据，用于回滚
    saved_neo4j_ids: List[str] = []
    saved_sqlite_ids: List[str] = []

    logger.info(f"开始保存 {len(characters)} 个人物到数据库")

    try:
        # Step 1: 保存到 Neo4j
        logger.info("Step 1: 保存到 Neo4j...")
        for char_data in characters:
            try:
                # 排除内部字段
                neo4j_data = {k: v for k, v in char_data.items() if k not in ['id', 'source', 'ai_version']}
                char = character_repo.create(novel_id, neo4j_data)
                if char:
                    saved_neo4j_ids.append(char.get("id"))
            except Exception as e:
                logger.error(f"保存人物到 Neo4j 失败: {e}")

        logger.info(f"Neo4j 保存完成，成功 {len(saved_neo4j_ids)} 个")

        # Step 2: 保存到 SQLite
        logger.info("Step 2: 保存到 SQLite...")
        for char_data in characters:
            char_id = char_data.get('id')
            source = char_data.get('source', 'ai')
            ai_version = char_data.get('ai_version', current_version)

            if char_id:
                # 更新现有人物
                existing = db.query(Character).filter(Character.id == char_id).first()
                if existing:
                    # 只更新 AI 生成的数据，保留用户修改的
                    if existing.source in ('user', 'ai_modified'):
                        # 保留用户修改的字段，只更新 AI 允许更新的字段
                        if char_data.get('aliases'):
                            existing_aliases = existing.aliases or []
                            for alias in char_data.get('aliases', []):
                                if alias not in existing_aliases:
                                    existing_aliases.append(alias)
                            existing.aliases = existing_aliases
                        existing.source = 'ai_modified'
                        existing.ai_version = ai_version
                    else:
                        # AI 数据可以完全更新
                        for key, value in char_data.items():
                            if key not in ['id', 'source', 'ai_version']:
                                setattr(existing, key, value)
                        existing.source = source
                        existing.ai_version = ai_version
                    saved_sqlite_ids.append(existing.id)
            else:
                # 新增人物
                new_char = Character(
                    novel_id=novel_id,
                    name=char_data.get('name', ''),
                    aliases=char_data.get('aliases', []),
                    basic_info=char_data.get('basic_info', {}),
                    personality=char_data.get('personality', []),
                    abilities=char_data.get('abilities', []),
                    story_summary=char_data.get('story_summary'),
                    first_appear=char_data.get('first_appear'),
                    source=source,
                    ai_version=ai_version,
                )
                db.add(new_char)
                db.flush()
                saved_sqlite_ids.append(new_char.id)

        logger.info(f"SQLite 保存完成，成功 {len(saved_sqlite_ids)} 个")

        # 更新小说的分析进度
        novel.last_analyzed_chapter = new_max_chapter
        novel.last_analyzed_at = datetime.utcnow()
        novel.analysis_version = current_version

        # 两边都成功，提交事务
        db.commit()
        logger.info(f"成功保存 {len(saved_neo4j_ids)} 个 Neo4j 人物, {len(saved_sqlite_ids)} 个 SQLite 人物")

    except Exception as e:
        logger.error(f"保存人物失败，开始回滚: {e}")

        # 回滚 Neo4j
        for char_id in saved_neo4j_ids:
            try:
                character_repo.delete(char_id)
            except Exception as rollback_error:
                logger.error(f"回滚 Neo4j 人物失败 {char_id}: {rollback_error}")

        # SQLite 自动回滚
        db.rollback()

        raise HTTPException(status_code=500, detail=f"保存人物失败: {str(e)}")

    # 返回所有人物
    logger.info("获取所有人物用于返回...")
    try:
        all_characters = character_repo.get_by_novel(novel_id) or []
        logger.info(f"从 Neo4j 获取到 {len(all_characters)} 个人物")
    except Exception as e:
        logger.warning(f"从 Neo4j 获取人物失败: {e}")
        all_characters = []

    if not all_characters:
        try:
            all_characters = db.query(Character).filter(Character.novel_id == novel_id).all()
            logger.info(f"从 SQLite 获取到 {len(all_characters)} 个人物")
            # 转换为可序列化的字典
            all_characters = [
                {
                    'id': c.id,
                    'name': c.name,
                    'aliases': c.aliases or [],
                    'basic_info': c.basic_info or {},
                    'personality': c.personality or [],
                    'abilities': c.abilities or [],
                    'story_summary': c.story_summary,
                    'first_appear': c.first_appear,
                    'novel_id': c.novel_id,
                    'source': c.source,
                    'ai_version': c.ai_version,
                    'created_at': c.created_at.isoformat() if c.created_at else None,
                    'updated_at': c.updated_at.isoformat() if c.updated_at else None,
                }
                for c in all_characters
            ]
        except Exception as e:
            logger.error(f"从 SQLite 获取人物失败: {e}")
            all_characters = []

    logger.info(f"准备返回响应: {len(all_characters)} 个人物")

    return ApiResponse(
        success=True,
        data={
            'characters': all_characters,
            'mode': mode,
            'analyzed_chapter': new_max_chapter,
            'version': current_version,
        }
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
    """更新人物信息（用户手动编辑会标记为 ai_modified）"""
    update_data = data.model_dump(exclude_unset=True)

    # 标记为用户修改
    update_data['source'] = 'ai_modified'

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
