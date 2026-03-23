from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import files, characters, plots, inspiration
from app.models.database import engine, Base

# 创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="小说创作助手 API",
    description="AI辅助小说创作的后端服务",
    version="1.0.0",
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js开发服务器
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(files.router, prefix="/api/files", tags=["文件"])
app.include_router(characters.router, prefix="/api/characters", tags=["人物"])
app.include_router(plots.router, prefix="/api/plots", tags=["情节"])
app.include_router(inspiration.router, prefix="/api/inspiration", tags=["灵感"])


@app.get("/")
async def root():
    return {"message": "小说创作助手 API 正在运行"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
