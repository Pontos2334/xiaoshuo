import logging
from typing import List, Dict, Any
from app.agent.client import ClaudeAgentClient
from app.core.json_utils import JSONParser

logger = logging.getLogger(__name__)

MAX_CONTENT_LENGTH = 15000  # 章节内容截断上限


class DeepConsistencyChecker:
    """深度一致性检查服务 - 检测小说中的逻辑矛盾"""

    def __init__(self):
        self.client = ClaudeAgentClient()
        self.json_parser = JSONParser()

    def _truncate(self, text: str) -> str:
        """截断章节内容到上限长度"""
        if len(text) > MAX_CONTENT_LENGTH:
            return text[:MAX_CONTENT_LENGTH] + "\n...(内容已截断)"
        return text

    async def check_dead_characters(
        self, characters_info: str, chapters_content: str
    ) -> List[Dict[str, Any]]:
        """
        检测已死亡角色的"复活"问题

        分析角色列表中的死亡事件，在章节内容中寻找死亡角色再次出现的矛盾。

        Args:
            characters_info: 角色信息（含死亡事件）
            chapters_content: 小说章节内容

        Returns:
            矛盾列表，每项包含 type, severity, description, chapter_a, chapter_b, suggestion
        """
        content = self._truncate(chapters_content)

        prompt = f"""你是一位专业的小说逻辑审校专家。你的任务是找出小说中"角色死后再次出现"的逻辑矛盾。

【角色信息】
{characters_info}

【小说章节内容】
{content}

---

请仔细阅读以上内容，找出所有"已经明确描写为死亡的角色在后续章节中又出现（有行动、对话、参与事件等）"的情况。

注意事项：
- 仅关注明确的死亡描写，不包含假死、复活等有伏笔的情节
- 如果角色只是被提及名字（如回忆、旁人提到）不算矛盾
- 注意区分同名不同人的情况

请返回JSON数组，每个元素包含以下字段：
- type: "character"
- severity: "error"（确凿矛盾）或 "warning"（可能矛盾）
- description: 详细描述矛盾内容（如"XXX在第X章已死亡，但在第X章又出现了..."）
- chapter_a: 死亡描写的章节标识（如"第3章"）
- chapter_b: 矛盾出现的章节标识（如"第7章"）
- suggestion: 修正建议

如果没有发现矛盾，返回空数组 []。只返回JSON，不要其他内容。"""

        response = await self.client.generate(prompt)
        result = self.json_parser.safe_parse_json(response, default=[])
        if not result:
            logger.info("角色死亡一致性检查：未发现问题")
        else:
            logger.info(f"角色死亡一致性检查：发现 {len(result)} 个问题")
        return result

    async def check_timeline(
        self, plot_nodes_info: str, chapters_content: str
    ) -> List[Dict[str, Any]]:
        """
        检测时间线矛盾

        分析情节节点和章节内容中的时间表述，找出时间线上的不一致。

        Args:
            plot_nodes_info: 情节节点信息
            chapters_content: 小说章节内容

        Returns:
            矛盾列表
        """
        content = self._truncate(chapters_content)

        prompt = f"""你是一位专业的小说逻辑审校专家。你的任务是找出小说中时间线方面的矛盾。

【情节节点信息】
{plot_nodes_info}

【小说章节内容】
{content}

---

请仔细分析文本中关于时间的所有线索（如"三天后""过了一夜""半年过去了""当天""翌日"等），找出时间线上的矛盾。

重点关注：
- 时间跨度矛盾（如A处说过了3天，B处暗示只过了1天）
- 季节矛盾（如某处说正值寒冬，另一处却描写盛夏景象）
- 年龄/年份矛盾（如角色年龄前后不一致）
- 事件顺序矛盾（如A应在B之后，但文本暗示A先发生）
- 同一时间点发生不可能同时发生的事件

请返回JSON数组，每个元素包含以下字段：
- type: "timeline"
- severity: "error"（确凿矛盾）或 "warning"（可能矛盾）
- description: 详细描述矛盾内容
- chapter_a: 第一个时间线索所在的章节标识
- chapter_b: 矛盾时间线索所在的章节标识
- suggestion: 修正建议

如果没有发现矛盾，返回空数组 []。只返回JSON，不要其他内容。"""

        response = await self.client.generate(prompt)
        result = self.json_parser.safe_parse_json(response, default=[])
        if not result:
            logger.info("时间线一致性检查：未发现问题")
        else:
            logger.info(f"时间线一致性检查：发现 {len(result)} 个问题")
        return result

    async def check_power_system(
        self, entities_info: str, chapters_content: str
    ) -> List[Dict[str, Any]]:
        """
        检测力量体系矛盾

        分析战斗描写和实力设定，找出力量等级方面的不一致。

        Args:
            entities_info: 实体/世界观信息（含力量体系设定）
            chapters_content: 小说章节内容

        Returns:
            矛盾列表
        """
        content = self._truncate(chapters_content)

        prompt = f"""你是一位专业的小说逻辑审校专家。你的任务是找出小说中力量体系（战力、能力等级、战斗表现）方面的矛盾。

【世界观与力量体系信息】
{entities_info}

【小说章节内容】
{content}

---

请仔细分析文本中关于力量体系的所有描写，找出矛盾之处。

重点关注：
- 战力等级矛盾（如某角色设定为初级，却能击败高级对手且无合理解释）
- 能力使用矛盾（如使用了未获得的能力，或已封印的能力无故恢复）
- 战斗表现矛盾（如同一角色在不同场景下实力表现差异巨大且无解释）
- 修炼/成长矛盾（如修炼时间极短却获得极高成就，且无天赋/奇遇等解释）
- 物品/装备矛盾（如使用了已消耗或被夺走的物品）

请返回JSON数组，每个元素包含以下字段：
- type: "power_system"
- severity: "error"（确凿矛盾）或 "warning"（可能矛盾）
- description: 详细描述矛盾内容
- chapter_a: 设定/首次描写的章节标识
- chapter_b: 矛盾出现的章节标识
- suggestion: 修正建议

如果没有发现矛盾，返回空数组 []。只返回JSON，不要其他内容。"""

        response = await self.client.generate(prompt)
        result = self.json_parser.safe_parse_json(response, default=[])
        if not result:
            logger.info("力量体系一致性检查：未发现问题")
        else:
            logger.info(f"力量体系一致性检查：发现 {len(result)} 个问题")
        return result

    async def check_geography(
        self, entities_info: str, chapters_content: str
    ) -> List[Dict[str, Any]]:
        """
        检测地理/行程矛盾

        分析地点描写和行程安排，找出空间移动方面的不合理之处。

        Args:
            entities_info: 实体/世界观信息（含地理设定）
            chapters_content: 小说章节内容

        Returns:
            矛盾列表
        """
        content = self._truncate(chapters_content)

        prompt = f"""你是一位专业的小说逻辑审校专家。你的任务是找出小说中地理方位和行程安排方面的矛盾。

【世界观与地理信息】
{entities_info}

【小说章节内容】
{content}

---

请仔细分析文本中关于地理位置、移动路线和旅行时间的描写，找出矛盾之处。

重点关注：
- 旅行时间矛盾（如A处说某地距此十天路程，B处角色一天就到了）
- 方位矛盾（如A在B的北方，但描写中角色向南走去B）
- 地理环境矛盾（如同一地点在不同章节的环境描写不一致）
- 空间逻辑矛盾（如在室内场景中突然出现室外的事物，或房间布局前后不一致）
- 不合理的行程安排（如在极短时间内跨越了遥远的距离）

请返回JSON数组，每个元素包含以下字段：
- type: "geography"
- severity: "error"（确凿矛盾）或 "warning"（可能矛盾）
- description: 详细描述矛盾内容
- chapter_a: 第一个地理线索所在的章节标识
- chapter_b: 矛盾地理线索所在的章节标识
- suggestion: 修正建议

如果没有发现矛盾，返回空数组 []。只返回JSON，不要其他内容。"""

        response = await self.client.generate(prompt)
        result = self.json_parser.safe_parse_json(response, default=[])
        if not result:
            logger.info("地理一致性检查：未发现问题")
        else:
            logger.info(f"地理一致性检查：发现 {len(result)} 个问题")
        return result

    async def check_naming(
        self, characters_info: str, chapters_content: str
    ) -> List[Dict[str, Any]]:
        """
        检测命名不一致问题

        分析角色/地点/组织的名称使用，找出同一实体使用不同名称且未解释的情况。

        Args:
            characters_info: 角色信息（含别名）
            chapters_content: 小说章节内容

        Returns:
            矛盾列表
        """
        content = self._truncate(chapters_content)

        prompt = f"""你是一位专业的小说逻辑审校专家。你的任务是找出小说中命名不一致的问题。

【角色信息（含别名/绰号）】
{characters_info}

【小说章节内容】
{content}

---

请仔细检查文本中的名称使用情况，找出命名不一致的问题。

重点关注：
- 同一角色使用了不同的名字，但文本中未给出解释（如别名、化名、称号等）
- 同一地点在不同章节有不同的叫法，但没有说明
- 同一组织/势力使用了不同名称，但没有交代
- 角色名称拼写或用字前后不一致（如"张三"变成了"张叁"）
- 称呼方式突变（如一直叫全名突然改叫绰号，且无场景变化的原因）

注意：以下情况不算矛盾：
- 已在角色别名中列出的名称
- 有合理解释的化名、伪装身份
- 不同角色对同一人使用不同称呼（符合人物关系）

请返回JSON数组，每个元素包含以下字段：
- type: "naming"
- severity: "error"（确凿矛盾）或 "warning"（可能矛盾）
- description: 详细描述命名不一致的内容
- chapter_a: 第一种命名出现的章节标识
- chapter_b: 另一种命名出现的章节标识
- suggestion: 修正建议

如果没有发现问题，返回空数组 []。只返回JSON，不要其他内容。"""

        response = await self.client.generate(prompt)
        result = self.json_parser.safe_parse_json(response, default=[])
        if not result:
            logger.info("命名一致性检查：未发现问题")
        else:
            logger.info(f"命名一致性检查：发现 {len(result)} 个问题")
        return result

    async def check_all(
        self,
        characters_info: str,
        plot_nodes_info: str,
        entities_info: str,
        chapters_content: str,
    ) -> List[Dict[str, Any]]:
        """
        执行全部一致性检查，合并结果

        Args:
            characters_info: 角色信息
            plot_nodes_info: 情节节点信息
            entities_info: 世界观/实体信息
            chapters_content: 小说章节内容

        Returns:
            全部检查结果的合并列表
        """
        import asyncio

        logger.info("开始执行全部一致性检查...")

        results = await asyncio.gather(
            self.check_dead_characters(characters_info, chapters_content),
            self.check_timeline(plot_nodes_info, chapters_content),
            self.check_power_system(entities_info, chapters_content),
            self.check_geography(entities_info, chapters_content),
            self.check_naming(characters_info, chapters_content),
            return_exceptions=True,
        )

        all_issues: List[Dict[str, Any]] = []
        check_names = [
            "角色死亡",
            "时间线",
            "力量体系",
            "地理",
            "命名",
        ]

        for name, result in zip(check_names, results):
            if isinstance(result, Exception):
                logger.error(f"{name}一致性检查失败: {result}")
            elif isinstance(result, list):
                all_issues.extend(result)
            else:
                logger.warning(f"{name}一致性检查返回了非列表结果: {type(result)}")

        # 按严重程度排序：error 优先
        severity_order = {"error": 0, "warning": 1}
        all_issues.sort(key=lambda x: severity_order.get(x.get("severity", "warning"), 1))

        logger.info(
            f"全部一致性检查完成，共发现 {len(all_issues)} 个问题 "
            f"(error: {sum(1 for i in all_issues if i.get('severity') == 'error')}, "
            f"warning: {sum(1 for i in all_issues if i.get('severity') == 'warning')})"
        )
        return all_issues
