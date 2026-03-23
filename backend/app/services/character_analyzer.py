import json
from typing import List, Dict, Any, Optional
from app.agent.client import ClaudeAgentClient


class CharacterAnalyzer:
    """人物分析服务"""

    def __init__(self):
        self.agent = ClaudeAgentClient()

    async def analyze(self, content: str) -> List[Dict[str, Any]]:
        """分析小说内容，提取人物信息"""
        prompt = f"""请分析以下小说内容，提取所有重要人物的信息。

小说内容：
{content[:10000]}  # 限制长度

请以JSON格式返回人物列表，每个人物包含以下字段：
- name: 姓名
- aliases: 别名/绰号列表
- basic_info: 基本信息（年龄、性别、身份等）
- personality: 性格特点列表
- abilities: 能力/技能列表
- story_summary: 角色故事简介
- first_appear: 首次出现的章节（如果有）

返回格式：
```json
[
  {{
    "name": "张三",
    "aliases": ["小张", "张老三"],
    "basic_info": {{"年龄": 25, "性别": "男", "身份": "剑客"}},
    "personality": ["勇敢", "正直"],
    "abilities": ["剑法", "轻功"],
    "story_summary": "...",
    "first_appear": "第一章"
  }}
]
```

只返回JSON数组，不要其他内容。"""

        response = await self.agent.generate(prompt)

        try:
            # 尝试解析JSON
            # 如果响应包含markdown代码块，提取其中的JSON
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response.strip()

            characters = json.loads(json_str)
            return characters
        except json.JSONDecodeError:
            # 如果解析失败，返回空列表
            return []

    async def analyze_relations(
        self,
        content: str,
        characters: List[Any]
    ) -> List[Dict[str, Any]]:
        """分析人物关系"""
        # 构建人物信息字符串
        char_info = "\n".join([
            f"- {c.name}（ID: {c.id}）：{getattr(c, 'story_summary', '暂无简介')}"
            for c in characters
        ])

        prompt = f"""请分析以下小说内容和人物列表，提取人物之间的关系。

小说内容：
{content[:8000]}

人物列表：
{char_info}

请以JSON格式返回关系列表，每个关系包含以下字段：
- source_id: 源人物ID
- target_id: 目标人物ID
- relation_type: 关系类型（如：师徒、朋友、敌人、恋人、亲人等）
- description: 关系描述
- strength: 关系强度（1-10）

返回格式：
```json
[
  {{
    "source_id": "人物ID",
    "target_id": "人物ID",
    "relation_type": "师徒",
    "description": "...",
    "strength": 8
  }}
]
```

只返回JSON数组，不要其他内容。"""

        response = await self.agent.generate(prompt)

        try:
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response.strip()

            relations = json.loads(json_str)
            return relations
        except json.JSONDecodeError:
            return []
