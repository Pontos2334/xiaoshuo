from typing import List, Any, Optional
from app.agent.client import ClaudeAgentClient


class InspirationGenerator:
    """灵感生成服务 - 基于原著设定生成忠实的内容建议"""

    def __init__(self):
        self.agent = ClaudeAgentClient()

    def _build_character_context(self, characters: List[Any], max_length: int = 1500) -> str:
        """构建详细的人物设定上下文"""
        if not characters:
            return ""

        context_parts = []
        total_length = 0

        for c in characters:
            char_text = f"""【{c.name}】
- 身份：{self._get_identity(c)}
- 性格特点：{self._get_personality(c)}
- 能力技能：{self._get_abilities(c)}
- 故事背景：{self._get_summary(c)}
- 别名绰号：{', '.join(c.aliases) if hasattr(c, 'aliases') and c.aliases else '无'}"""

            if total_length + len(char_text) > max_length:
                break
            context_parts.append(char_text)
            total_length += len(char_text)

        return "\n\n".join(context_parts)

    def _build_plot_context(self, plot_nodes: List[Any], max_length: int = 1000) -> str:
        """构建情节上下文"""
        if not plot_nodes:
            return ""

        context_parts = []
        total_length = 0

        for p in sorted(plot_nodes, key=lambda x: x.chapter if x.chapter else 0):
            plot_text = f"""【第{p.chapter}章：{p.title}】
- 情节概述：{p.summary or '暂无'}
- 主要情绪：{p.emotion or '未知'}
- 涉及人物：{', '.join(p.characters) if hasattr(p, 'characters') and p.characters else '未知'}
- 原文参考：{(p.content_ref or '')[:200]}"""

            if total_length + len(plot_text) > max_length:
                break
            context_parts.append(plot_text)
            total_length += len(plot_text)

        return "\n\n".join(context_parts)

    def _get_style_constraints(self) -> str:
        """获取写作风格约束"""
        return """【重要约束 - 必须严格遵守】
1. **忠实原著设定**：所有建议必须完全基于已提供的人物设定和情节背景，不得创造与原著矛盾的内容
2. **保持人物一致性**：人物的行为、对话风格、性格表现必须与给定设定完全一致
3. **延续已有风格**：模仿原著的叙事风格和语言特点
4. **不创造新设定**：不要添加新的人物背景、世界观设定或能力体系
5. **不改变已确立的关系**：人物关系必须与原著保持一致

如果原著信息不足，请明确指出"原著暂无相关设定"，而不是自行编造。"""

    def _get_style_guide(self) -> str:
        """获取风格指南"""
        return """【写作风格指南】
- 对话要符合人物性格，有辨识度
- 描写要具体，避免空洞的形容词
- 情节推进要有逻辑，符合人物动机
- 情感表达要自然，不刻意煽情
- 细节要服务于整体，不堆砌"""

    async def generate_scene_inspiration(
        self,
        characters: List[Any],
        plot_nodes: List[Any],
        original_text: Optional[str] = None,
        context: Optional[str] = None
    ) -> str:
        """基于选定的人物和情节生成场景灵感"""

        char_context = self._build_character_context(characters)
        plot_context = self._build_plot_context(plot_nodes)

        # 原文风格参考
        style_reference = ""
        if original_text:
            style_reference = f"""【原文风格参考】（以下片段展示了原著的写作风格）
{original_text[:800]}
"""

        prompt = f"""你是一位专业的小说创作顾问，正在帮助作者延续其正在创作的小说。

{self._get_style_constraints()}

{self._get_style_guide()}

---

【已确立的人物设定】
{char_context if char_context else '（未选择人物）'}

【已发生的情节】
{plot_context if plot_context else '（未选择情节）'}

{style_reference}

{f"【作者需求】{context}" if context else ""}

---

请基于以上**已有的、确定的**设定，提供场景创作建议。

要求：
1. **场景构想**：基于这些人物的性格和已有情节，他们可能产生什么互动？描述1-2个**符合原著逻辑**的场景方向（不要具体写出来，只给方向建议）

2. **对话风格**：分析每个人物的说话特点，给出**符合其性格**的对话要点（不是具体对话，而是风格指导）

3. **情绪处理**：这个场景应该传递什么情绪？如何通过人物的反应来体现？

4. **写作提示**：基于原著风格，这个场景应该注意什么？

请用简洁、实用的语言回答。记住：你的角色是帮助作者更好地写他/她自己的故事，而不是替作者创造新内容。"""

        return await self.agent.generate(prompt)

    async def generate_plot_inspiration(
        self,
        plot_nodes: List[Any],
        characters: List[Any],
        original_text: Optional[str] = None,
        context: Optional[str] = None
    ) -> str:
        """为指定情节生成写作灵感"""

        plot_context = self._build_plot_context(plot_nodes)
        char_context = self._build_character_context(characters, max_length=800)

        style_reference = ""
        if original_text:
            style_reference = f"""【原文风格参考】
{original_text[:600]}
"""

        prompt = f"""你是一位专业的小说创作顾问。

{self._get_style_constraints()}

---

【当前情节】
{plot_context if plot_context else '（未选择情节）'}

【相关人物】
{char_context if char_context else '（未选择人物）'}

{style_reference}

{f"【作者需求】{context}" if context else ""}

---

请基于已有设定，为这个情节提供写作建议：

1. **情节深化方向**：基于现有设定，这个情节可以从哪些角度深入？（不要创造新的设定或人物背景）

2. **人物表现建议**：涉及的人物在这个情节中应该如何表现才符合其性格？

3. **情绪渲染**：如何强化当前情绪？给出具体的、符合原著风格的建议

4. **细节建议**：可以添加哪些**符合世界观**的细节描写？

请确保所有建议都基于已提供的信息，不要编造新设定。"""

        return await self.agent.generate(prompt)

    async def generate_continue_inspiration(
        self,
        characters: List[Any],
        plot_nodes: List[Any],
        original_text: Optional[str] = None,
        context: Optional[str] = None
    ) -> str:
        """生成后续情节发展建议"""

        char_context = self._build_character_context(characters[:8], max_length=1200)

        # 只取最近的情节
        recent_plots = sorted(plot_nodes, key=lambda x: x.chapter if x.chapter else 0)[-8:] if plot_nodes else []
        plot_context = self._build_plot_context(recent_plots, max_length=800)

        style_reference = ""
        if original_text:
            style_reference = f"""【原文风格参考】
{original_text[:600]}
"""

        prompt = f"""你是一位专业的小说创作顾问。

{self._get_style_constraints()}

---

【主要人物设定】
{char_context if char_context else '（暂无人物信息）'}

【最近情节】
{plot_context if plot_context else '（暂无情节信息）'}

{style_reference}

{f"【作者需求】{context}" if context else ""}

---

请基于**已有的**人物设定和情节发展，提供后续方向建议：

1. **人物驱动**：基于各人物的**已确立**性格和动机，他们接下来可能有什么行动？（不是创造新的动机，而是分析已有的）

2. **线索延续**：已有的情节中有什么可以继续发展的线索？

3. **可能的方向**：给出2-3个**符合原著逻辑**的发展方向（不要创造新设定，只分析可能性）

4. **需要注意的点**：在继续写作时，哪些已确立的设定需要保持一致？

记住：你的建议应该帮助作者更好地延续他/她自己的故事，而不是把故事引向完全不同的方向。"""

        return await self.agent.generate(prompt)

    async def generate_character_inspiration(
        self,
        characters: List[Any],
        plot_nodes: List[Any],
        original_text: Optional[str] = None,
        context: Optional[str] = None
    ) -> str:
        """为指定角色生成发展建议"""

        char_context = self._build_character_context(characters, max_length=2000)

        related_plots = ""
        if plot_nodes:
            related_plots = "【角色相关情节】\n" + "\n".join([
                f"- 第{p.chapter}章：{p.title}"
                for p in plot_nodes[:5]
            ])

        style_reference = ""
        if original_text:
            style_reference = f"""【角色在原文中的表现】
{original_text[:600]}
"""

        prompt = f"""你是一位专业的小说创作顾问。

{self._get_style_constraints()}

---

【角色详细设定】
{char_context if char_context else '（未选择角色）'}

{related_plots}

{style_reference}

{f"【作者需求】{context}" if context else ""}

---

请基于**已确立的角色设定**，提供角色发展建议：

1. **角色内核**：基于已有的性格特点，这个角色的核心是什么？（分析而非创造）

2. **内在矛盾**：从**已有的**性格特点中，可以挖掘出什么内在矛盾？

3. **成长空间**：在**不改变角色本质**的前提下，这个角色可以如何成长？

4. **表现建议**：如何更好地展现这个角色**已有的**特点？

5. **边界提醒**：在写作这个角色时，哪些**已确立的设定**不能违背？

不要为角色添加新的背景故事或能力，所有建议都要基于已提供的信息。"""

        return await self.agent.generate(prompt)

    async def generate_emotion_inspiration(
        self,
        plot_nodes: List[Any],
        characters: List[Any],
        original_text: Optional[str] = None,
        context: Optional[str] = None
    ) -> str:
        """为指定情节生成情绪渲染建议"""

        plot_context = self._build_plot_context(plot_nodes)
        char_context = self._build_character_context(characters, max_length=600)

        # 提取目标情绪
        target_emotion = ""
        if plot_nodes:
            emotions = [p.emotion for p in plot_nodes if p.emotion]
            if emotions:
                target_emotion = f"【目标情绪】：{', '.join(emotions)}"

        style_reference = ""
        if original_text:
            style_reference = f"""【原文情绪表达示例】
{original_text[:500]}
"""

        prompt = f"""你是一位专业的小说创作顾问。

{self._get_style_constraints()}

---

【当前情节】
{plot_context if plot_context else '（未选择情节）'}

{target_emotion}

【涉及人物】
{char_context if char_context else '（未选择人物）'}

{style_reference}

{f"【作者需求】{context}" if context else ""}

---

请提供情绪渲染建议：

1. **情绪基调**：基于情节内容，应该传递什么核心情绪？

2. **人物反应**：基于各人物的**已有性格**，他们会有什么情绪反应？

3. **环境烘托**：可以用什么样的环境描写来烘托情绪？（保持与世界观一致）

4. **节奏控制**：如何通过叙事节奏来强化情绪效果？

5. **具体技巧**：给出2-3个**符合原著风格**的情绪表达技巧

所有建议都要基于已提供的人物设定和世界观，不要创造新的设定。"""

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
                return ', '.join(char.personality[:5])
            return str(char.personality)
        return '性格未知'

    def _get_summary(self, char) -> str:
        """获取人物简介"""
        return getattr(char, 'story_summary', '暂无') or '暂无'

    def _get_basic_info(self, char) -> str:
        """获取基本信息"""
        if hasattr(char, 'basic_info') and char.basic_info:
            if isinstance(char.basic_info, dict):
                items = [f"{k}: {v}" for k, v in char.basic_info.items()]
                return ', '.join(items)
            return str(char.basic_info)
        return '未知'

    def _get_abilities(self, char) -> str:
        """获取人物能力"""
        if hasattr(char, 'abilities') and char.abilities:
            if isinstance(char.abilities, list):
                return ', '.join(char.abilities[:5])
            return str(char.abilities)
        return '未知'
