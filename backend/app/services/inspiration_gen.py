from typing import List, Any, Optional
from app.agent.client import ClaudeAgentClient


class InspirationGenerator:
    """灵感生成服务"""

    def __init__(self):
        self.agent = ClaudeAgentClient()

    async def generate_scene_inspiration(
        self,
        characters: List[Any],
        plot_nodes: List[Any],
        context: Optional[str] = None
    ) -> str:
        """基于选定的人物和情节生成场景灵感"""
        # 构建人物信息
        char_info = ""
        if characters:
            char_info = "选定的人物：\n" + "\n".join([
                f"""- **{c.name}**
  身份：{self._get_identity(c)}
  性格：{self._get_personality(c)}
  简介：{self._get_summary(c)[:100]}"""
                for c in characters
            ])

        # 构建情节信息
        plot_info = ""
        if plot_nodes:
            plot_info = "选定的情节：\n" + "\n".join([
                f"- 第{p.chapter}章 **{p.title}**：{p.summary[:80] if p.summary else ''}...（情绪：{p.emotion or '未知'}）"
                for p in sorted(plot_nodes, key=lambda x: x.chapter if x.chapter else 0)
            ])

        # 分析人物关系
        relationship_hint = ""
        if len(characters) >= 2:
            names = [c.name for c in characters]
            relationship_hint = f"\n\n请注意这些人物之间可能存在的关系互动：{', '.join(names)}"

        prompt = f"""你是一位资深的小说创作顾问。请基于以下选定的人物和情节，生成场景描写灵感和创作建议。

{char_info}

{plot_info}
{relationship_hint}

{f"作者额外说明：{context}" if context else ""}

请从以下几个角度提供详细的创作灵感：

1. **场景构想**：这些人物在这些情节中可能产生什么样的互动场景？请描述2-3个可能的场景。

2. **冲突与张力**：这些人物之间可能产生什么矛盾或冲突？如何利用情节背景制造张力？

3. **对话灵感**：给出一些精彩的对话片段示例，体现人物性格和关系。

4. **心理描写**：如何深入刻画人物在这些场景中的内心活动？

5. **情节推进**：基于选定的人物组合，可以如何推动情节发展？有什么意想不到的展开方向？

6. **氛围营造**：如何通过环境、节奏和细节描写来烘托场景氛围？

请用中文回答，语言生动有感染力，提供具体可操作的创作建议。"""

        return await self.agent.generate(prompt)

    async def generate_plot_inspiration(
        self,
        plot_nodes: List[Any],
        characters: List[Any],
        context: Optional[str] = None
    ) -> str:
        """为指定情节生成写作灵感"""
        # 构建上下文
        plot_info = ""
        if plot_nodes:
            plot_info = "选定情节：\n" + "\n".join([
                f"""- 第{p.chapter}章 **{p.title}**
  概述：{p.summary or '暂无'}
  主要情绪：{p.emotion or '未知'}
  重要程度：{p.importance or 5}/10"""
                for p in plot_nodes
            ])

        char_info = ""
        if characters:
            char_info = "涉及角色：\n" + "\n".join([
                f"- {c.name}：{self._get_summary(c)[:100]}"
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
5. **情绪渲染**：如何增强当前情绪的表达？

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
                f"- {c.name}（{self._get_personality(c)}）"
                for c in characters[:10]  # 限制数量
            ])

        # 构建情节概要
        plot_info = ""
        if plot_nodes:
            plot_info = "已发生的情节：\n" + "\n".join([
                f"- 第{p.chapter}章 {p.title}：{(p.summary or '')[:50]}..."
                for p in sorted(plot_nodes, key=lambda x: x.chapter if x.chapter else 0)[-10:]  # 只取最近10个
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
        characters: List[Any],
        plot_nodes: List[Any],
        context: Optional[str] = None
    ) -> str:
        """为指定角色生成发展建议"""
        char_info = ""
        if characters:
            char_info = "选定角色：\n" + "\n".join([
                f"""- **{c.name}**
  别名/绰号：{', '.join(c.aliases) if hasattr(c, 'aliases') and c.aliases else '无'}
  基本信息：{self._get_basic_info(c)}
  性格特点：{self._get_personality(c)}
  能力/技能：{self._get_abilities(c)}
  故事简介：{self._get_summary(c)}"""
                for c in characters
            ])

        plot_context = ""
        if plot_nodes:
            plot_context = "相关情节：\n" + "\n".join([
                f"- 第{p.chapter}章 {p.title}"
                for p in plot_nodes[:5]
            ])

        prompt = f"""你是一位资深的小说创作顾问。请为以下角色提供发展建议。

{char_info}

{plot_context}

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
        plot_nodes: List[Any],
        characters: List[Any],
        context: Optional[str] = None
    ) -> str:
        """为指定情节生成情绪渲染建议"""
        plot_info = ""
        if plot_nodes:
            plot_info = "选定情节：\n" + "\n".join([
                f"""- 第{p.chapter}章 **{p.title}**
  概述：{p.summary or '暂无'}
  目标情绪：{p.emotion or '未知'}"""
                for p in plot_nodes
            ])

        char_info = ""
        if characters:
            char_info = "涉及人物：\n" + "\n".join([
                f"- {c.name}（{self._get_personality(c)[:20]}）"
                for c in characters
            ])

        prompt = f"""你是一位资深的小说创作顾问。请为以下情节提供情绪渲染的建议。

{plot_info}

{char_info}

{f"作者额外说明：{context}" if context else ""}

请从以下几个角度提供建议：
1. **场景描写**：如何通过环境描写烘托情绪？
2. **人物反应**：人物应该如何表达情绪？
3. **对话设计**：如何通过对话传递情绪？
4. **节奏控制**：如何控制叙事节奏来强化情绪？
5. **感官描写**：可以加入哪些感官细节？

请用中文回答，提供具体可操作的写作技巧。"""

        return await self.agent.generate(prompt)

    # 辅助方法
    def _get_identity(self, char) -> str:
        """获取人物身份"""
        if hasattr(char, 'basic_info') and char.basic_info:
            if isinstance(char.basic_info, dict):
                return char.basic_info.get('身份', '未知')
            return getattr(char.basic_info, '身份', '未知')
        return '未知'

    def _get_personality(self, char) -> str:
        """获取人物性格"""
        if hasattr(char, 'personality') and char.personality:
            if isinstance(char.personality, list):
                return ', '.join(char.personality[:3])
            return str(char.personality)
        return '性格未知'

    def _get_summary(self, char) -> str:
        """获取人物简介"""
        return getattr(char, 'story_summary', '暂无') or '暂无'

    def _get_basic_info(self, char) -> str:
        """获取基本信息"""
        if hasattr(char, 'basic_info') and char.basic_info:
            if isinstance(char.basic_info, dict):
                return str(char.basic_info)
            return str(char.basic_info)
        return '未知'

    def _get_abilities(self, char) -> str:
        """获取人物能力"""
        if hasattr(char, 'abilities') and char.abilities:
            if isinstance(char.abilities, list):
                return ', '.join(char.abilities)
            return str(char.abilities)
        return '未知'
