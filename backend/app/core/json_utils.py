import json
import re
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


class JSONParser:
    """统一的JSON解析工具"""

    @staticmethod
    def extract_json_from_response(response: str) -> str:
        """从AI响应中提取JSON字符串"""
        patterns = [
            r'```json\s*([\s\S]*?)\s*```',
            r'```\s*([\s\S]*?)\s*```',
        ]
        for pattern in patterns:
            match = re.search(pattern, response)
            if match:
                return match.group(1).strip()
        return response.strip()

    @staticmethod
    def _repair_json(json_str: str) -> str:
        """尝试修复常见的 JSON 格式错误"""
        # 移除单行注释
        json_str = re.sub(r'//.*?$', '', json_str, flags=re.MULTILINE)
        # 移除多行注释
        json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)

        # 修复尾逗号 (}, ] 前的逗号)
        json_str = re.sub(r',\s*([}\]])', r'\1', json_str)

        # 修复单引号为双引号（简单场景）
        # 只在键值对中使用单引号的情况
        json_str = re.sub(r"(?<=[\[{,:\s])'([^']*)'(?=[\]}\s:,])", r'"\1"', json_str)

        # 尝试修复截断的 JSON 数组
        stripped = json_str.strip()
        if stripped.startswith('[') and not stripped.endswith(']'):
            # 找到最后一个完整的对象
            last_brace = stripped.rfind('}')
            if last_brace > 0:
                json_str = stripped[:last_brace + 1] + ']'
                logger.info(f"修复截断的 JSON 数组，截取到位置 {last_brace}")

        # 尝试修复截断的 JSON 对象
        if stripped.startswith('{') and not stripped.endswith('}'):
            last_brace = stripped.rfind('}')
            if last_brace > 0:
                json_str = stripped[:last_brace + 1] + '}'

        return json_str

    @staticmethod
    def parse_json(response: str) -> Any:
        """解析JSON，失败时抛出 ValueError"""
        json_str = JSONParser.extract_json_from_response(response)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # 尝试修复
            repaired = JSONParser._repair_json(json_str)
            try:
                return json.loads(repaired)
            except json.JSONDecodeError as e:
                logger.warning(f"JSON解析失败（修复后仍无效）: {e}, 原始响应: {json_str[:200]}...")
                raise ValueError(f"JSON解析失败: {e}")

    @staticmethod
    def safe_parse_json(response: str, default: Any = None) -> Any:
        """安全解析JSON，失败时返回默认值而不抛出异常"""
        json_str = JSONParser.extract_json_from_response(response)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # 尝试修复
            repaired = JSONParser._repair_json(json_str)
            try:
                result = json.loads(repaired)
                logger.info(f"JSON 修复成功")
                return result
            except json.JSONDecodeError as e:
                logger.warning(f"JSON解析失败，返回默认值: {e}, 原始响应: {response[:200]}...")
                return default
