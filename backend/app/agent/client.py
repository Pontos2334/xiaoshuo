import os
from typing import Optional
from dotenv import load_dotenv
import anthropic

# 加载环境变量
load_dotenv()


class ClaudeAgentClient:
    """Claude Agent客户端，支持智谱AI等兼容API"""

    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.base_url = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
        self.model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
        self.max_tokens = int(os.getenv("MAX_TOKENS", "4096"))

        if self.api_key:
            self.client = anthropic.Anthropic(
                api_key=self.api_key,
                base_url=self.base_url
            )
        else:
            self.client = None
            print("警告: 未配置ANTHROPIC_API_KEY，将使用模拟响应")

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """生成响应"""
        if self.client:
            try:
                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    system=system_prompt or "你是一位专业的小说创作顾问，擅长分析文学作品和提供创作建议。请用中文回答。",
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                return message.content[0].text
            except Exception as e:
                print(f"API调用错误: {e}")
                return self._mock_response(prompt)
        else:
            return self._mock_response(prompt)

    def generate_sync(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """同步生成响应"""
        if self.client:
            try:
                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    system=system_prompt or "你是一位专业的小说创作顾问，擅长分析文学作品和提供创作建议。请用中文回答。",
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                return message.content[0].text
            except Exception as e:
                print(f"API调用错误: {e}")
                return self._mock_response(prompt)
        else:
            return self._mock_response(prompt)

    def _mock_response(self, prompt: str) -> str:
        """模拟响应（用于测试或无API密钥时）"""
        if "人物" in prompt or "角色" in prompt:
            return '''```json
[
  {
    "name": "李云",
    "aliases": ["小李", "云少"],
    "basic_info": {"年龄": "18岁", "性别": "男", "身份": "山村少年"},
    "personality": ["勇敢", "善良", "好奇心强", "有时冲动"],
    "abilities": ["剑心通明", "剑术天赋"],
    "story_summary": "普通山村少年，因救了神秘女子苏瑶而踏上冒险之路，展现出惊人的剑道天赋。",
    "first_appear": "第一章"
  },
  {
    "name": "苏瑶",
    "aliases": ["天机圣女", "神秘女子"],
    "basic_info": {"年龄": "20岁", "性别": "女", "身份": "天机阁圣女"},
    "personality": ["外冷内热", "聪慧", "有担当", "神秘"],
    "abilities": ["暗器", "轻功", "天机秘术"],
    "story_summary": "天机阁圣女，掌握着一个足以颠覆武林的秘密，被暗影楼追杀中。",
    "first_appear": "第一章"
  },
  {
    "name": "暗影楼主",
    "aliases": ["楼主"],
    "basic_info": {"年龄": "未知", "性别": "未知", "身份": "暗影楼首领"},
    "personality": ["神秘", "狠辣", "野心勃勃"],
    "abilities": ["暗影秘术", "杀手组织"],
    "story_summary": "神秘反派，追杀苏瑶，企图夺取天机阁的秘密。",
    "first_appear": "第二章"
  }
]
```'''
        elif "情节" in prompt:
            return '''```json
[
  {
    "title": "命运的开端",
    "chapter": "第一章",
    "summary": "李云在村后禁地发现被追杀的神秘女子苏瑶，命运齿轮开始转动。苏瑶请求李云救她，李云做出了改变人生的决定。",
    "characters": ["李云", "苏瑶"],
    "emotion": "紧张",
    "importance": 9,
    "content_ref": "那一天的夕阳，李云永远不会忘记..."
  },
  {
    "title": "逃亡之路",
    "chapter": "第二章",
    "summary": "苏瑶告知李云自己的身份和追杀者，两人连夜离开村子。暗影楼的杀手正在逼近。",
    "characters": ["李云", "苏瑶", "暗影楼杀手"],
    "emotion": "紧张",
    "importance": 8,
    "content_ref": "苏瑶的真实身份，远比李云想象的要复杂得多..."
  },
  {
    "title": "剑意初醒",
    "chapter": "第三章",
    "summary": "逃亡路上，苏瑶教导李云武艺。李云展现出剑心通明的天赋，暗影楼杀手再次出现。",
    "characters": ["李云", "苏瑶", "暗影楼杀手"],
    "emotion": "紧张",
    "importance": 8,
    "content_ref": "记住，剑不是用力量去挥舞的，而是用心..."
  },
  {
    "title": "生死之战",
    "chapter": "第四章",
    "summary": "李云独自面对三名暗影楼高手，领悟剑心通明，以木剑击败敌人。苏瑶震惊于他的天赋。",
    "characters": ["李云", "苏瑶"],
    "emotion": "热血",
    "importance": 9,
    "content_ref": "那一刻，天地间仿佛只剩下这一剑..."
  }
]
```'''
        elif "关系" in prompt:
            return '''```json
[
  {
    "source_id": "李云ID",
    "target_id": "苏瑶ID",
    "relation_type": "师徒",
    "description": "苏瑶教导李云武艺，两人建立深厚的信任关系",
    "strength": 8
  },
  {
    "source_id": "李云ID",
    "target_id": "暗影楼主ID",
    "relation_type": "敌人",
    "description": "暗影楼追杀苏瑶，李云因此与暗影楼为敌",
    "strength": 9
  },
  {
    "source_id": "苏瑶ID",
    "target_id": "暗影楼主ID",
    "relation_type": "敌人",
    "description": "暗影楼追杀苏瑶，企图夺取天机阁秘密",
    "strength": 10
  }
]
```'''
        elif "连接" in prompt:
            return '''```json
[
  {
    "source_id": "情节1ID",
    "target_id": "情节2ID",
    "connection_type": "cause",
    "description": "李云救苏瑶导致被卷入纷争，必须逃亡"
  },
  {
    "source_id": "情节2ID",
    "target_id": "情节3ID",
    "connection_type": "next",
    "description": "逃亡过程中开始学习武艺"
  },
  {
    "source_id": "情节3ID",
    "target_id": "情节4ID",
    "connection_type": "cause",
    "description": "学习武艺展现天赋，为战斗做准备"
  }
]
```'''
        elif "灵感" in prompt or "建议" in prompt:
            return """
## 写作灵感建议

### 1. 情节发展建议
- 可以在李云与苏瑶的互动中增加更多情感层次，从最初的陌生到逐渐信任
- 考虑添加一些小插曲展现李云的性格特点，如善良、勇敢
- 暗影楼的威胁可以更加具体化，让读者感受到紧迫感

### 2. 冲突设计
- 内在冲突：李云对未知世界的恐惧与对冒险的渴望
- 外在冲突：暗影楼的持续追杀与李云能力的不足
- 可以设计一个两难选择：保护苏瑶还是保护村子？

### 3. 伏笔建议
- 李云的剑心通明天赋来源可以是一个伏笔
- 苏瑶掌握的秘密可以逐步透露
- 暗影楼主的身份可以设置悬念

### 4. 人物塑造
- 通过细节展现李云的成长：从一开始的慌乱到后来的冷静
- 苏瑶的神秘感与人性温暖的平衡
- 配角也可以有独特的性格特点

### 5. 情绪渲染技巧
- 使用环境描写烘托氛围：夕阳、迷雾、月光
- 通过人物反应展现情绪：握紧拳头、呼吸急促
- 对话中蕴含情感，而非直接说明
"""
        else:
            return "这是一个模拟响应。请检查API配置。"
