"""
安全相关工具

提供路径验证、API Key 认证等安全功能
"""

import os
import logging
from typing import List, Optional

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

logger = logging.getLogger(__name__)


def is_path_allowed(path: str) -> bool:
    """
    检查路径是否在允许扫描的根目录范围内。

    如果 SCAN_ALLOWED_ROOTS 未配置（空字符串），则允许所有路径（开发模式）。
    否则，路径必须 resolve 到其中一个允许的根目录下。
    """
    allowed_roots = settings.SCAN_ALLOWED_ROOTS.strip()
    if not allowed_roots:
        # 未配置白名单，不限制（仅适合开发环境）
        return True

    roots = [r.strip() for r in allowed_roots.split(",") if r.strip()]
    if not roots:
        return True

    try:
        resolved = os.path.realpath(path)
    except Exception:
        return False

    for root in roots:
        try:
            root_resolved = os.path.realpath(root)
            if resolved.startswith(root_resolved + os.sep) or resolved == root_resolved:
                return True
        except Exception:
            continue

    return False


def validate_scan_path(path: str) -> str:
    """
    验证扫描路径是否合法。

    Returns:
        验证后的路径

    Raises:
        ValueError: 路径不在允许范围内
    """
    # 解析为绝对路径
    abs_path = os.path.abspath(path)

    # 阻止明显的敏感路径
    blocked_parts = {"/etc", "/proc", "/sys", "/root", "/var/log",
                     "C:\\Windows", "C:\\ProgramData"}
    for blocked in blocked_parts:
        if abs_path.startswith(blocked):
            raise ValueError(f"不允许扫描系统目录: {abs_path}")

    # 检查白名单
    if not is_path_allowed(abs_path):
        allowed_roots = settings.SCAN_ALLOWED_ROOTS.strip()
        raise ValueError(
            f"路径不在允许范围内: {abs_path}。"
            f"请配置 SCAN_ALLOWED_ROOTS 环境变量指定允许的目录"
        )

    return abs_path


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    可选的 API Key 认证中间件。

    当 settings.API_KEY 非空时启用认证。
    跳过 health check 和 OPTIONS 预检请求。
    """

    async def dispatch(self, request: Request, call_next):
        if not settings.API_KEY:
            # 未配置 API Key，跳过认证
            return await call_next(request)

        # 跳过健康检查
        if request.url.path in ("/", "/health", "/docs", "/openapi.json"):
            return await call_next(request)

        # 跳过 OPTIONS 预检
        if request.method == "OPTIONS":
            return await call_next(request)

        # 检查 API Key
        api_key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
        if api_key != settings.API_KEY:
            logger.warning(f"API Key 认证失败: {request.url.path} (来源: {request.client.host if request.client else 'unknown'})")
            raise HTTPException(status_code=401, detail="无效的 API Key")

        return await call_next(request)
