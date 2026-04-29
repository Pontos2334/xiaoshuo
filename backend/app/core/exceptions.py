from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from typing import Any, List
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# 获取允许的 CORS origins
def _get_cors_origins() -> List[str]:
    try:
        return settings.allowed_cors_origins
    except Exception:
        return ["http://localhost:3000", "http://127.0.0.1:3000"]


class AppException(Exception):
    """应用自定义异常基类"""
    def __init__(self, message: str, code: str = "UNKNOWN_ERROR", details: Any = None):
        self.message = message
        self.code = code
        self.details = details
        super().__init__(self.message)


class JSONParseError(AppException):
    """JSON解析异常"""
    def __init__(self, raw_response: str):
        super().__init__(
            message="AI响应解析失败",
            code="JSON_PARSE_ERROR",
            details={"raw_response": raw_response[:500]}
        )


class FileOperationError(AppException):
    """文件操作异常"""
    def __init__(self, operation: str, path: str, original_error: str):
        super().__init__(
            message=f"文件操作失败: {operation}",
            code="FILE_OPERATION_ERROR",
            details={"path": path, "error": original_error}
        )


class NovelNotFoundError(AppException):
    """小说不存在异常"""
    def __init__(self, novel_id: str):
        super().__init__(
            message="小说不存在",
            code="NOVEL_NOT_FOUND",
            details={"novel_id": novel_id}
        )


def _add_cors_headers(response: JSONResponse, request: Request) -> JSONResponse:
    """为响应添加 CORS 头，确保异常响应也能被浏览器读取"""
    origin = request.headers.get("origin", "")
    allowed_origins = _get_cors_origins()
    if origin in allowed_origins or "*" in allowed_origins:
        response.headers["Access-Control-Allow-Origin"] = origin or allowed_origins[0]
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Vary"] = "Origin"
    return response


async def app_exception_handler(request: Request, exc: AppException):
    logger.error(f"AppException: {exc.code} - {exc.message}", extra={"details": exc.details})
    return _add_cors_headers(JSONResponse(
        status_code=400,
        content={"success": False, "error": exc.message, "code": exc.code}
    ), request)


async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(f"HTTP {exc.status_code}: {exc.detail}")
    return _add_cors_headers(JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": exc.detail, "code": f"HTTP_{exc.status_code}"}
    ), request)


async def generic_exception_handler(request: Request, exc: Exception):
    import traceback
    logger.exception(f"Unhandled exception: {type(exc).__name__}: {str(exc)}\n{traceback.format_exc()}")
    try:
        return _add_cors_headers(JSONResponse(
            status_code=500,
            content={"success": False, "error": "服务器内部错误", "code": "INTERNAL_ERROR"}
        ), request)
    except Exception:
        # 极限兜底：确保无论如何都返回带 CORS 头的响应
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "服务器内部错误", "code": "INTERNAL_ERROR"},
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Credentials": "true",
            }
        )
