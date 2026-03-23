import json
from typing import List, Dict, Any, Optional
from app.agent.client import ClaudeAgentClient


class PlotAnalyzer:
    """情节分析服务"""

    def __init__(self):
        self.agent = ClaudeAgentClient()

    async def analyze(self, content: str, outline: str = "") -> List[Dict[str, Any]]:
        """分析小说内容，提取情节节点"""
        prompt = f"""请分析以下小说内容和大纲，提取主要情节节点。

小说大纲：
{outline[:5000] if outline else "暂无大纲"}

小说内容：
{content[:15000]}

请以JSON格式返回情节节点列表，每个节点包含以下字段：
- title: 情节标题
- chapter: 所属章节
- summary: 情节概述（100-200字）
- characters: 涉及的人物名称列表
- emotion: 主要情绪（紧张/温馨/悲伤/欢乐/愤怒/平静）
- importance: 重要程度（1-10）
- content_ref: 原文关键引用（50字以内）

返回格式：
```json
[
  {{
    "title": "初入江湖",
    "chapter": "第一章",
    "summary": "...",
    "characters": ["张三", "李四"],
    "emotion": "紧张",
    "importance": 8,
    "content_ref": "..."
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

            plot_nodes = json.loads(json_str)
            return plot_nodes
        except json.JSONDecodeError:
            return []

    async def analyze_connections(
        self,
        plot_nodes: List[Any]
    ) -> List[Dict[str, Any]]:
        """分析情节之间的连接关系"""
        # 构建情节信息字符串
        plot_info = "\n".join([
            f"- [{n.id}] {n.title}（第{n.chapter}章）：{n.summary[:100]}..."
            for n in plot_nodes
        ])

        prompt = f"""请分析以下情节节点之间的连接关系。

情节列表：
{plot_info}

请以JSON格式返回连接列表，每个连接包含以下字段：
- source_id: 源情节ID
- target_id: 目标情节ID
- connection_type: 连接类型（cause因果/parallel并行/foreshadow伏笔/flashback闪回/next后续）
- description: 连接描述

返回格式：
```json
[
  {{
    "source_id": "情节ID",
    "target_id": "情节ID",
    "connection_type": "cause",
    "description": "..."
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

            connections = json.loads(json_str)
            return connections
        except json.JSONDecodeError:
            return []
