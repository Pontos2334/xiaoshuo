"""大纲管理 API"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import logging
import json

from app.models.database import get_db
from app.models.models import Novel, OutlineNode
from app.models.schemas import (
    OutlineNodeCreate, OutlineNodeUpdate, OutlineNodeResponse, ApiResponse
)
from app.core.file_utils import safe_read_file
from app.core.json_utils import JSONParser

router = APIRouter()
logger = logging.getLogger(__name__)


# ========== CRUD ==========

@router.get("", response_model=List[OutlineNodeResponse])
async def get_outline_tree(novel_id: str, db: Session = Depends(get_db)):
    """获取大纲树形结构"""
    novel = db.query(Novel).filter(Novel.id == novel_id).first()
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")

    nodes = db.query(OutlineNode).filter(
        OutlineNode.novel_id == novel_id
    ).order_by(OutlineNode.level, OutlineNode.sort_order).all()

    return _build_tree(nodes)


@router.get("/{node_id}", response_model=OutlineNodeResponse)
async def get_outline_node(node_id: str, db: Session = Depends(get_db)):
    """获取大纲节点详情"""
    node = db.query(OutlineNode).filter(OutlineNode.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="大纲节点不存在")

    # 获取子节点
    children = db.query(OutlineNode).filter(
        OutlineNode.parent_id == node_id
    ).order_by(OutlineNode.sort_order).all()

    resp = _node_to_response(node)
    resp["children"] = [_node_to_response(c) for c in children]
    return resp


@router.post("", response_model=OutlineNodeResponse)
async def create_outline_node(data: OutlineNodeCreate, db: Session = Depends(get_db)):
    """创建大纲节点"""
    novel = db.query(Novel).filter(Novel.id == data.novel_id).first()
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")

    if data.parent_id:
        parent = db.query(OutlineNode).filter(OutlineNode.id == data.parent_id).first()
        if not parent:
            raise HTTPException(status_code=404, detail="父节点不存在")

    node = OutlineNode(
        novel_id=data.novel_id,
        parent_id=data.parent_id,
        level=data.level,
        title=data.title,
        content=data.content,
        chapter_range=data.chapter_range,
        status=data.status,
        sort_order=data.sort_order,
        ai_context=data.ai_context,
    )
    db.add(node)
    db.commit()
    db.refresh(node)
    return _node_to_response(node)


@router.put("/{node_id}", response_model=OutlineNodeResponse)
async def update_outline_node(
    node_id: str,
    update: OutlineNodeUpdate,
    db: Session = Depends(get_db)
):
    """更新大纲节点"""
    node = db.query(OutlineNode).filter(OutlineNode.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="大纲节点不存在")

    update_dict = update.model_dump(exclude_none=True)
    for key, value in update_dict.items():
        setattr(node, key, value)

    db.commit()
    db.refresh(node)
    return _node_to_response(node)


@router.delete("/{node_id}", response_model=ApiResponse)
async def delete_outline_node(node_id: str, db: Session = Depends(get_db)):
    """删除大纲节点及其所有子节点（级联删除）"""
    node = db.query(OutlineNode).filter(OutlineNode.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="大纲节点不存在")

    title = node.title
    # 递归收集所有后代节点ID
    descendant_ids = _collect_descendant_ids(node_id, db)

    # 删除后代（从最深层开始）
    for did in reversed(descendant_ids):
        child = db.query(OutlineNode).filter(OutlineNode.id == did).first()
        if child:
            db.delete(child)

    # 删除自身
    db.delete(node)
    db.commit()
    return ApiResponse(success=True, data={"message": f"已删除大纲节点「{title}」及其{len(descendant_ids)}个子节点"})


@router.put("/reorder", response_model=ApiResponse)
async def reorder_outline_nodes(
    novel_id: str,
    node_ids: List[str],
    db: Session = Depends(get_db)
):
    """重排同级节点顺序"""
    novel = db.query(Novel).filter(Novel.id == novel_id).first()
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")

    for index, node_id in enumerate(node_ids):
        node = db.query(OutlineNode).filter(
            OutlineNode.id == node_id,
            OutlineNode.novel_id == novel_id
        ).first()
        if node:
            node.sort_order = index

    db.commit()
    return ApiResponse(success=True, data={"message": "大纲节点顺序已更新"})


# ========== AI 功能 ==========

@router.post("/generate-master", response_model=ApiResponse)
async def generate_master_outline(novel_id: str, db: Session = Depends(get_db)):
    """AI 生成顶层大纲"""
    novel = db.query(Novel).filter(Novel.id == novel_id).first()
    if not novel:
        raise HTTPException(status_code=404, detail="小说不存在")

    content = safe_read_file(novel.content_path) if novel.content_path else ""
    if not content:
        return ApiResponse(success=False, error="小说内容为空")

    text_sample = content[:8000]

    # 获取已有的人物和情节信息作为上下文
    from app.models.models import Character, PlotNode
    characters = db.query(Character).filter(Character.novel_id == novel_id).all()
    plots = db.query(PlotNode).filter(PlotNode.novel_id == novel_id).all()

    char_info = ", ".join(c.name for c in characters[:15]) if characters else "暂无人物数据"
    plot_info = "; ".join(f"{p.title}({p.chapter})" for p in plots[:15]) if plots else "暂无情节数据"

    try:
        from app.agent.client import ClaudeAgentClient
        client = ClaudeAgentClient()

        prompt = f"""请为以下小说生成一个顶层大纲（总纲级别）。

小说文本（部分）：
{text_sample}

已有信息：
- 人物: {char_info}
- 情节: {plot_info}

生成要求：
1. 创建一个总纲（level=0），概括全书主题和主线
2. 将全书分为几个大卷/阶段（level=1），每个包含章节范围
3. 每卷应有清晰的叙事目标和转折点

以JSON格式输出：
```json
{{
  "outline": [
    {{
      "level": 0,
      "title": "总纲标题",
      "content": "全书概述（主题、主线、核心冲突）",
      "chapter_range": "第1-{total}章",
      "status": "draft",
      "sort_order": 0,
      "children": [
        {{
          "level": 1,
          "title": "卷名",
          "content": "本卷概述",
          "chapter_range": "第X-Y章",
          "status": "draft",
          "sort_order": 0
        }}
      ]
    }}
  ]
}}
```"""

        response = await client.generate(prompt)
        if not response:
            return ApiResponse(success=False, error="AI生成失败")

        data = JSONParser.safe_parse_json(response)
        if not data or "outline" not in data:
            return ApiResponse(success=False, error="AI响应格式错误")

        saved = _save_outline_tree(novel_id, data["outline"], parent_id=None, db=db)

        return ApiResponse(
            success=True,
            data={
                "count": len(saved),
                "outline": [_node_to_response(s) for s in saved]
            }
        )
    except Exception as e:
        logger.error(f"AI生成大纲失败: {e}")
        return ApiResponse(success=False, error=str(e))


@router.post("/{node_id}/breakdown", response_model=ApiResponse)
async def breakdown_outline_node(node_id: str, db: Session = Depends(get_db)):
    """AI 将大纲节点拆分为子节点"""
    node = db.query(OutlineNode).filter(OutlineNode.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="大纲节点不存在")

    novel = db.query(Novel).filter(Novel.id == node.novel_id).first()
    content = safe_read_file(novel.content_path) if novel and novel.content_path else ""
    text_sample = content[:4000] if content else "（无小说文本）"

    try:
        from app.agent.client import ClaudeAgentClient
        client = ClaudeAgentClient()

        prompt = f"""请将以下大纲节点拆分为更详细的子节点。

父节点：
- 标题: {node.title}
- 层级: {node.level}
- 内容: {node.content or '无'}
- 章节范围: {node.chapter_range or '未指定'}

小说文本（参考）：
{text_sample}

拆分要求：
1. 将该节点拆分为3-8个子节点
2. 子节点层级为 {node.level + 1}
3. 每个子节点应包含明确的叙事目标
4. 按时间/逻辑顺序排列

以JSON格式输出：
```json
{{
  "children": [
    {{
      "title": "子节点标题",
      "content": "详细内容描述",
      "chapter_range": "第X-Y章",
      "status": "draft",
      "sort_order": 0
    }}
  ]
}}
```"""

        response = await client.generate(prompt)
        if not response:
            return ApiResponse(success=False, error="AI生成失败")

        data = JSONParser.safe_parse_json(response)
        if not data or "children" not in data:
            return ApiResponse(success=False, error="AI响应格式错误")

        saved = []
        for idx, item in enumerate(data["children"]):
            child = OutlineNode(
                novel_id=node.novel_id,
                parent_id=node_id,
                level=node.level + 1,
                title=item.get("title", f"子节点{idx + 1}"),
                content=item.get("content"),
                chapter_range=item.get("chapter_range"),
                status=item.get("status", "draft"),
                sort_order=item.get("sort_order", idx),
            )
            db.add(child)
            saved.append(child)

        db.commit()
        for s in saved:
            db.refresh(s)

        return ApiResponse(
            success=True,
            data={
                "parent_id": node_id,
                "count": len(saved),
                "children": [_node_to_response(s) for s in saved]
            }
        )
    except Exception as e:
        logger.error(f"AI拆分大纲失败: {e}")
        return ApiResponse(success=False, error=str(e))


@router.post("/{node_id}/expand", response_model=ApiResponse)
async def expand_outline_node(node_id: str, db: Session = Depends(get_db)):
    """AI 将大纲节点扩展为详细节拍"""
    node = db.query(OutlineNode).filter(OutlineNode.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="大纲节点不存在")

    novel = db.query(Novel).filter(Novel.id == node.novel_id).first()
    content = safe_read_file(novel.content_path) if novel and novel.content_path else ""
    text_sample = content[:4000] if content else "（无小说文本）"

    # 获取兄弟节点作为上下文
    siblings = []
    if node.parent_id:
        siblings = db.query(OutlineNode).filter(
            OutlineNode.parent_id == node.parent_id,
            OutlineNode.id != node_id
        ).order_by(OutlineNode.sort_order).all()

    sibling_info = ""
    if siblings:
        sibling_info = "相邻节点: " + "; ".join(f"{s.title}({s.chapter_range or '未指定'})" for s in siblings)

    try:
        from app.agent.client import ClaudeAgentClient
        client = ClaudeAgentClient()

        prompt = f"""请将以下大纲节点扩展为详细的写作节拍（beats）。

大纲节点：
- 标题: {node.title}
- 层级: {node.level}
- 内容: {node.content or '无'}
- 章节范围: {node.chapter_range or '未指定'}
{sibling_info}

小说文本（参考）：
{text_sample}

扩展要求：
1. 将该节点展开为5-15个具体的写作节拍
2. 每个节拍包含：场景描述、涉及人物、情绪基调、关键对话要点
3. 保持叙事节奏的起伏变化
4. 节拍之间有逻辑递进关系

以JSON格式输出：
```json
{{
  "expanded_content": "扩展后的完整大纲内容（自然语言描述）",
  "beats": [
    {{
      "beat_number": 1,
      "scene": "场景描述",
      "characters": ["涉及人物"],
      "emotion": "情绪基调",
      "key_dialogue_hint": "关键对话要点",
      "pacing": "快/慢/中"
    }}
  ]
}}
```"""

        response = await client.generate(prompt)
        if not response:
            return ApiResponse(success=False, error="AI生成失败")

        data = JSONParser.safe_parse_json(response)
        if not data:
            return ApiResponse(success=False, error="AI响应格式错误")

        # 将扩展内容保存到节点的 ai_context 中
        node.ai_context = {
            "expanded_content": data.get("expanded_content", ""),
            "beats": data.get("beats", []),
        }
        db.commit()
        db.refresh(node)

        return ApiResponse(
            success=True,
            data={
                "node_id": node_id,
                "expanded_content": data.get("expanded_content", ""),
                "beats": data.get("beats", []),
            }
        )
    except Exception as e:
        logger.error(f"AI扩展大纲失败: {e}")
        return ApiResponse(success=False, error=str(e))


# ========== 辅助函数 ==========

def _build_tree(nodes: List[OutlineNode]) -> List[dict]:
    """将扁平节点列表构建为树形结构"""
    node_map = {}
    for node in nodes:
        node_map[node.id] = _node_to_response(node)
        node_map[node.id]["children"] = []

    roots = []
    for node in nodes:
        resp = node_map[node.id]
        if node.parent_id and node.parent_id in node_map:
            node_map[node.parent_id]["children"].append(resp)
        else:
            roots.append(resp)

    return roots


def _node_to_response(node: OutlineNode) -> dict:
    """将 ORM 对象转为响应字典"""
    ai_ctx = node.ai_context
    if isinstance(ai_ctx, str):
        try:
            ai_ctx = json.loads(ai_ctx)
        except json.JSONDecodeError:
            ai_ctx = None

    return {
        "id": node.id,
        "novel_id": node.novel_id,
        "parent_id": node.parent_id,
        "level": node.level,
        "title": node.title,
        "content": node.content,
        "chapter_range": node.chapter_range,
        "status": node.status,
        "sort_order": node.sort_order,
        "ai_context": ai_ctx,
        "children": [],
        "created_at": node.created_at,
        "updated_at": node.updated_at,
    }


def _collect_descendant_ids(node_id: str, db: Session) -> List[str]:
    """递归收集所有后代节点ID（BFS）"""
    ids = []
    queue = [node_id]

    while queue:
        current = queue.pop(0)
        children = db.query(OutlineNode).filter(
            OutlineNode.parent_id == current
        ).all()
        for child in children:
            ids.append(child.id)
            queue.append(child.id)

    return ids


def _save_outline_tree(
    novel_id: str,
    items: List[dict],
    parent_id: Optional[str],
    db: Session
) -> List[OutlineNode]:
    """递归保存大纲树到数据库"""
    saved = []

    for item in items:
        node = OutlineNode(
            novel_id=novel_id,
            parent_id=parent_id,
            level=item.get("level", 0),
            title=item.get("title", "未命名"),
            content=item.get("content"),
            chapter_range=item.get("chapter_range"),
            status=item.get("status", "draft"),
            sort_order=item.get("sort_order", 0),
        )
        db.add(node)
        db.flush()  # 获取ID用于子节点关联
        saved.append(node)

        # 递归处理子节点
        children = item.get("children", [])
        if children:
            child_saved = _save_outline_tree(novel_id, children, node.id, db)
            saved.extend(child_saved)

    return saved

