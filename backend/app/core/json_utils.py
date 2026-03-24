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
    def parse_json(response: str) -> Any:
        """解析JSON，失败时抛出 ValueError"""
        json_str = JSONParser.extract_json_from_response(response)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON解析失败: {e}, 原始响应: {json_str[:200]}...")
            raise ValueError(f"JSON解析失败: {e}")

    @staticmethod
    def safe_parse_json(response: str, default: Any = None) -> Any:
        """安全解析JSON，失败时返回默认值而不抛出异常"""
        json_str = JSONParser.extract_json_from_response(response)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON解析失败，返回默认值: {e}, 原始响应: {response[:200]}...")
            return default
