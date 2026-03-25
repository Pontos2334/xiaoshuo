from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.api import files, characters, plots, inspiration, search, graph, chat, assistant
from app.models.database import engine, Base
from app.core.logging_config import setup_logging
from app.core.config import settings
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    http_exception_handler,
    generic_exception_handler
)

# 初始化日志
setup_logging(level="INFO")

# 创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="小说创作助手 API",
    description="AI辅助小说创作的后端服务",
    version="1.0.0",
)

# 注册全局异常处理器
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# CORS配置 - 使用统一的配置类
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
    max_age=600,
)

# 注册路由
app.include_router(files.router, prefix="/api/files", tags=["文件"])
app.include_router(characters.router, prefix="/api/characters", tags=["人物"])
app.include_router(plots.router, prefix="/api/plots", tags=["情节"])
app.include_router(inspiration.router, prefix="/api/inspiration", tags=["灵感"])
app.include_router(search.router, prefix="/api/search", tags=["搜索"])
app.include_router(graph.router, prefix="/api/graph", tags=["图谱"])
app.include_router(chat.router, prefix="/api/chat", tags=["对话"])
app.include_router(assistant.router, prefix="/api/assistant", tags=["智能助手"])


@app.get("/")
async def root():
    return {"message": "小说创作助手 API 正在运行"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
