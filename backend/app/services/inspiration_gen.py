from typing import List, Any, Optional
from app.agent.client import ClaudeAgentClient


class InspirationGenerator:
    """灵感生成服务"""

    def __init__(self):
        self.agent = ClaudeAgentClient()

    async def generate_plot_inspiration(
        self,
        plot_node: Optional[Any],
        characters: List[Any],
        context: Optional[str] = None
    ) -> str:
        """为指定情节生成写作灵感"""
        # 构建上下文
        plot_info = ""
        if plot_node:
            plot_info = f"""
当前情节：{plot_node.title}
章节：第{plot_node.chapter}章
概述：{plot_node.summary}
主要情绪：{plot_node.emotion}
重要程度：{plot_node.importance}/10
"""

        char_info = ""
        if characters:
            char_info = "涉及角色：\n" + "\n".join([
                f"- {c.name}：{getattr(c, 'story_summary', '暂无简介')[:100]}"
                for c in characters
            ])

        prompt = f"""你是一位资深的小说创作顾问。请为以下情节提供写作灵感和建议。

{plot_info}

{char_info}

{f"作者额外说明：{context}" if context else ""}

请从以下几个角度提供建议：
1. **情节发展建议**：如何让这个情节更加引人入胜？
2. **冲突设计**：可以添加什么样的冲突或矛盾？
3. **伏笔建议**：可以埋下什么样的伏笔？
4. **人物塑造**：如何通过这个情节深化人物形象？
5. **情绪渲染**：如何增强{plot_node.emotion if plot_node else '当前'}情绪的表达？

请用中文回答，语言生动有感染力。"""

        return await self.agent.generate(prompt)

    async def generate_continue_inspiration(
        self,
        characters: List[Any],
        plot_nodes: List[Any],
        context: Optional[str] = None
    ) -> str:
        """生成后续情节发展建议"""
        # 构建角色信息
        char_info = ""
        if characters:
            char_info = "主要角色：\n" + "\n".join([
                f"- {c.name}（{', '.join(c.personality[:3]) if hasattr(c, 'personality') and c.personality else '性格未知'}）"
                for c in characters[:10]  # 限制数量
            ])

        # 构建情节概要
        plot_info = ""
        if plot_nodes:
            plot_info = "已发生的情节：\n" + "\n".join([
                f"- 第{p.chapter}章 {p.title}：{p.summary[:50]}..."
                for p in sorted(plot_nodes, key=lambda x: x.chapter)[-10:]  # 只取最近10个
            ])

        prompt = f"""你是一位资深的小说创作顾问。请基于以下信息，提供后续情节发展的建议。

{char_info}

{plot_info}

{f"作者额外说明：{context}" if context else ""}

请从以下几个角度提供建议：
1. **近期发展方向**：接下来1-3章可以写什么？
2. **中期规划**：5-10章后的故事走向建议
3. **高潮设计**：可以考虑什么样的高潮情节？
4. **角色发展**：哪些角色需要更多的戏份和发展？
5. **悬念设置**：如何让读者保持阅读兴趣？

请用中文回答，提供具体可行的建议。"""

        return await self.agent.generate(prompt)

    async def generate_character_inspiration(
        self,
        character: Optional[Any],
        context: Optional[str] = None
    ) -> str:
        """为指定角色生成发展建议"""
        char_info = ""
        if character:
            char_info = f"""
角色名称：{character.name}
别名/绰号：{', '.join(character.aliases) if hasattr(character, 'aliases') and character.aliases else '无'}
基本信息：{character.basic_info if hasattr(character, 'basic_info') else '未知'}
性格特点：{', '.join(character.personality) if hasattr(character, 'personality') and character.personality else '未知'}
能力/技能：{', '.join(character.abilities) if hasattr(character, 'abilities') and character.abilities else '未知'}
故事简介：{character.story_summary if hasattr(character, 'story_summary') else '暂无'}
"""

        prompt = f"""你是一位资深的小说创作顾问。请为以下角色提供发展建议。

{char_info}

{f"作者额外说明：{context}" if context else ""}

请从以下几个角度提供建议：
1. **角色弧线**：这个角色应该有怎样的成长轨迹？
2. **内在冲突**：角色内心可以有什么样的矛盾和挣扎？
3. **外在挑战**：角色应该面对什么样的挑战？
4. **关系发展**：角色与其他人物的关系如何发展？
5. **关键转折**：角色的命运转折点可能是什么？

请用中文回答，深入挖掘角色的潜力。"""

        return await self.agent.generate(prompt)

    async def generate_emotion_inspiration(
        self,
        plot_node: Optional[Any],
        context: Optional[str] = None
    ) -> str:
        """为指定情节生成情绪渲染建议"""
        plot_info = ""
        if plot_node:
            plot_info = f"""
情节：{plot_node.title}
章节：第{plot_node.chapter}章
概述：{plot_node.summary}
目标情绪：{plot_node.emotion}
"""

        prompt = f"""你是一位资深的小说创作顾问。请为以下情节提供情绪渲染的建议。

{plot_info}

{f"作者额外说明：{context}" if context else ""}

请从以下几个角度提供建议：
1. **场景描写**：如何通过环境描写烘托情绪？
2. **人物反应**：人物应该如何表达情绪？
3. **对话设计**：如何通过对话传递情绪？
4. **节奏控制**：如何控制叙事节奏来强化情绪？
5. **感官描写**：可以加入哪些感官细节？

请用中文回答，提供具体可操作的写作技巧。"""

        return await self.agent.generate(prompt)
