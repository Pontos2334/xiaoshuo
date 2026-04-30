"""
基础模型测试
"""

from app.models.models import Novel, Character, CharacterRelation, PlotNode


def test_create_novel(db_session):
    """测试创建小说"""
    novel = Novel(name="测试小说", path="/test/path")
    db_session.add(novel)
    db_session.commit()

    assert novel.id is not None
    assert novel.name == "测试小说"
    assert novel.chapter_count == 0
    assert novel.word_count == 0


def test_create_character(db_session):
    """测试创建人物"""
    novel = Novel(name="测试小说", path="/test/path")
    db_session.add(novel)
    db_session.commit()

    character = Character(
        novel_id=novel.id,
        name="张三",
        aliases=["小张", "三哥"],
        personality=["勇敢", "善良"],
        story_summary="测试人物简介"
    )
    db_session.add(character)
    db_session.commit()

    assert character.id is not None
    assert character.name == "张三"
    assert character.aliases == ["小张", "三哥"]


def test_create_character_relation(db_session):
    """测试创建人物关系"""
    novel = Novel(name="测试小说", path="/test/path")
    db_session.add(novel)
    db_session.commit()

    char1 = Character(novel_id=novel.id, name="张三")
    char2 = Character(novel_id=novel.id, name="李四")
    db_session.add_all([char1, char2])
    db_session.commit()

    relation = CharacterRelation(
        novel_id=novel.id,
        source_id=char1.id,
        target_id=char2.id,
        relation_type="朋友",
        description="测试关系",
        strength=7
    )
    db_session.add(relation)
    db_session.commit()

    assert relation.id is not None
    assert relation.relation_type == "朋友"
    assert relation.strength == 7


def test_create_plot_node(db_session):
    """测试创建情节节点"""
    novel = Novel(name="测试小说", path="/test/path")
    db_session.add(novel)
    db_session.commit()

    plot = PlotNode(
        novel_id=novel.id,
        title="初遇",
        chapter="第一章",
        summary="测试情节概述",
        emotion="紧张",
        importance=8
    )
    db_session.add(plot)
    db_session.commit()

    assert plot.id is not None
    assert plot.title == "初遇"
    assert plot.importance == 8


def test_novel_cascade_delete(db_session):
    """测试级联删除"""
    novel = Novel(name="测试小说", path="/test/path")
    db_session.add(novel)
    db_session.commit()

    char = Character(novel_id=novel.id, name="张三")
    db_session.add(char)
    db_session.commit()

    # 删除小说，人物应被级联删除
    db_session.delete(novel)
    db_session.commit()

    remaining = db_session.query(Character).filter_by(id=char.id).first()
    assert remaining is None
