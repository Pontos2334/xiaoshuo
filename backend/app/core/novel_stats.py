"""
小说统计服务

统一管理小说的章节数、字数等统计信息的更新
避免多处独立修改导致数据不一致
"""

import logging
from sqlalchemy.orm import Session
from app.models.models import Novel, Chapter
from app.core.file_utils import safe_read_file

logger = logging.getLogger(__name__)


def refresh_novel_stats(db: Session, novel: Novel) -> None:
    """
    从数据库中已有数据刷新小说统计信息（章节数、字数）。

    这是唯一的统计信息更新入口，避免其他地方独立修改。
    """
    # 统计章节数
    chapter_count = db.query(Chapter).filter(Chapter.novel_id == novel.id).count()

    # 统计总字数
    total_words = 0
    chapters = db.query(Chapter).filter(Chapter.novel_id == novel.id).all()
    for ch in chapters:
        total_words += ch.word_count or 0

    novel.chapter_count = chapter_count
    novel.word_count = total_words
    db.commit()
    logger.info(f"刷新小说统计: {novel.name}, 章节={chapter_count}, 字数={total_words}")


def estimate_stats_from_content(novel: Novel) -> dict:
    """
    从原始内容估算统计信息（用于首次扫描，不写入数据库）。

    Returns:
        {"chapter_count": int, "word_count": int}
    """
    if not novel.content_path:
        return {"chapter_count": 0, "word_count": 0}

    content = safe_read_file(novel.content_path) or ""
    import re
    chapter_matches = re.findall(r'第[一二三四五六七八九十百千万零\d]+章', content)
    chapter_count = len(chapter_matches)
    word_count = len(content)

    return {"chapter_count": chapter_count, "word_count": word_count}
