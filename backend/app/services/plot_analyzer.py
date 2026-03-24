import logging
from typing import List, Dict, Any
from app.agent.client import ClaudeAgentClient
from app.core.json_utils import JSONParser

logger = logging.getLogger(__name__)

# 常量定义
MAX_CONTENT_LENGTH = 15000
MAX_OUTLINE_LENGTH = 5000


class PlotAnalyzer:
    """情节分析服务"""

    def __init__(self):
        self.agent = ClaudeAgentClient()
        self.json_parser = JSONParser()

    async def analyze(self, content: str, outline: str = "") -> List[Dict[str, Any]]:
        """分析小说内容，提取情节节点"""
        truncated_outline = outline[:MAX_OUTLINE_LENGTH] if outline else "暂无大纲"
        truncated_content = content[:MAX_CONTENT_LENGTH]

        prompt = f"""请分析以下小说内容和大纲，提取主要情节节点。

小说大纲：
{truncated_outline}

小说内容：
{truncated_content}

请以JSON格式返回情节节点列表，每个节点包含以下字段：
- title: 情节标题
- chapter: 所属章节
- summary: 情节概述（100-200字）
- characters: 涉及的人物名称列表
- emotion: 主要情绪（紧张/温馨/悲伤/欢乐/愤怒/平静）
- importance: 重要程度（1-10）
- content_ref: 原文关键引用（50字以内）

只返回JSON数组，不要其他内容。"""

        response = await self.agent.generate(prompt)

        plot_nodes = self.json_parser.safe_parse_json(response, default=[])
        if not plot_nodes:
            logger.warning(f"情节分析返回空结果，原始响应: {response[:200]}...")
        return plot_nodes

    async def analyze_connections(self, plot_nodes: List[Any]) -> List[Dict[str, Any]]:
        """分析情节之间的连接关系"""
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

只返回JSON数组，不要其他内容。"""

        response = await self.agent.generate(prompt)

        connections = self.json_parser.safe_parse_json(response, default=[])
        if not connections:
            logger.warning(f"连接分析返回空结果，原始响应: {response[:200]}...")
        return connections
