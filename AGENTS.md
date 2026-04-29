# AGENTS.md — AI小说创作助手代码指南

本文件为在本仓库中工作的AI编码代理提供指导。

## 项目概述

AI小说创作助手 — 一个基于AI的Web应用，提供人物关系图、情节关联图、灵感提示、向量搜索、知识图谱（GraphRAG）和人物对话功能。

- **前端**: Next.js 16.2 + React 19.2 + TypeScript（端口 3000）
- **后端**: FastAPI + SQLAlchemy + SQLite + Neo4j + Qdrant（端口 8002）
- **AI**: 智谱AI GLM-5，通过Anthropic兼容API调用

## 构建 / Lint / 测试命令

### 前端（在 `frontend/` 目录）

```bash
npm install                  # 安装依赖
npm run dev                  # 启动开发服务器（端口 3000）
npm run build                # 生产构建
npm run lint                 # ESLint 检查
```

### 后端（在 `backend/` 目录）

```bash
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

### Docker（根目录）

```bash
docker-compose up -d         # 启动后端 + 前端 + Qdrant + Neo4j
```

### Windows 脚本

```bash
install.bat                  # 安装所有依赖
start.bat                    # 启动前后端服务
```

### 服务地址

| 服务 | URL |
|------|-----|
| 前端 | http://localhost:3000 |
| 后端 API | http://localhost:8002 |
| API 文档 (Swagger) | http://localhost:8002/docs |
| Neo4j 控制台 | http://localhost:7474 |
| Qdrant 控制台 | http://localhost:6333/dashboard |

## 代码风格 — Python（后端）

### 格式化 & Lint

未配置格式化工具/linter（没有 ruff、black、flake8 或 pyproject.toml）。严格遵循现有代码模式。

### 规范

- **导入顺序**: stdlib → 第三方库 → 本地模块，用空行分隔
- **类型标注**: 使用 `typing` 模块的 `List`、`Optional`、`Dict`；请求/响应使用 Pydantic 模型
- **命名**: 函数/变量用 `snake_case`，类用 `PascalCase`，常量用 `UPPER_CASE`
- **错误处理**: 使用 `app/core/exceptions.py` 中的自定义 `AppException`；全局异常处理器在 `main.py` 注册
- **日志**: 使用 `logging.getLogger(__name__)`，不要用 `print()`
- **配置**: Pydantic `BaseSettings` 在 `app/core/config.py`，从 `.env` 加载
- **API 层**: FastAPI 路由在 `app/api/`，按领域分文件（characters、plots、files 等）
- **服务层**: 业务逻辑在 `app/services/`，由 API 处理器调用
- **数据库**: SQLAlchemy 模型在 `app/models/`，仓储模式在 `app/db/`

### 示例模式

```python
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.schemas import CharacterResponse

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/", response_model=List[CharacterResponse])
async def get_characters(novel_id: str, db: Session = Depends(get_db)):
    logger.info(f"get_characters called with novel_id={novel_id}")
    # ... 实现
```

## 代码风格 — TypeScript（前端）

### ESLint

ESLint 9 使用 flat config（`eslint.config.mjs`）。使用 `eslint-config-next`（core-web-vitals + TypeScript）。提交前运行 `npm run lint`。

### 规范

- **路径别名**: `@/*` 映射到 `./src/*`（在 tsconfig.json 中配置）
- **导入顺序**: React/Next.js → 第三方库 → 本地模块，使用 `@/` 绝对路径
- **组件**: 文件名 PascalCase（如 `CharacterGraph.tsx`），目录名 kebab-case
- **类型**: 共享类型在 `src/types/`，接口以领域名称开头（如 `Character`、`PlotNode`）
- **状态**: Zustand stores 在 `src/stores/index.ts` — 五个 store：Novel、Character、Plot、Inspiration、UI
- **API 调用**: Axios 实例在 `src/lib/api.ts`，60秒超时；错误使用 toast 通知
- **样式**: Tailwind CSS 4 + shadcn/ui 组件在 `src/components/ui/`
- **图谱**: AntV G6 v5 用于人物关系图，@xyflow/react v12 用于情节关联图

### 示例模式

```typescript
import { api } from '@/lib/api';
import { Character } from '@/types';
import { useCharacterStore } from '@/stores';

async function fetchCharacters(novelId: string): Promise<Character[]> {
  const response = await api.get('/characters', { params: { novel_id: novelId } });
  return response.data;
}
```

## 架构

### 前端

```
src/
├── app/              # Next.js 页面（App Router）
├── components/
│   ├── CharacterGraph/   # AntV G6 人物关系图
│   ├── PlotGraph/        # ReactFlow 情节关联图
│   ├── InspirationPanel/ # AI 灵感面板
│   ├── Layout/           # 布局组件
│   ├── FileSelector/     # 小说文件夹选择器
│   └── ui/               # shadcn/ui 基础组件
├── stores/           # Zustand 状态管理
├── types/            # TypeScript 类型定义
└── lib/              # 工具函数（api.ts 等）
```

### 后端

```
backend/app/
├── main.py           # FastAPI 入口，路由注册
├── api/              # 路由处理器（files、characters、plots 等）
├── services/         # 业务逻辑（analyzers、vector、graph_rag、chat）
├── models/           # SQLAlchemy 模型 + Pydantic schemas
├── core/             # 配置、异常、日志
├── agent/            # LLM 客户端（Anthropic 兼容）
├── db/               # Neo4j 仓储模式
└── __init__.py
```

### 关键数据流

1. **小说导入**: 文件夹扫描 → `backend/data/novels/` → SQLite 元数据
2. **AI 分析**: 读取文本 → LLM API → 解析 JSON → 存入 SQLite/Neo4j
3. **可视化**: 前端调用 API → SQLite 查询 → 转换为 G6/ReactFlow 格式
4. **向量搜索**: 文本 → embedding → Qdrant 存储/检索

## 环境配置

后端从 `backend/.env` 读取配置：

```env
ANTHROPIC_API_KEY=your_key
ANTHROPIC_BASE_URL=https://open.bigmodel.cn/api/anthropic
CLAUDE_MODEL=glm-5
MAX_TOKENS=4096
DATABASE_URL=sqlite:///./novel_assistant.db
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
QDRANT_URL=http://localhost:6333
EMBEDDING_USE_LOCAL=true
```

## 重要注意事项

- **Next.js 16 / React 19**: 与训练数据有 breaking changes — 编写代码前先查看 `node_modules/next/dist/docs/`
- **Mock 数据**: 后端无 API Key 时返回 mock 响应（见 `agent/client.py:_mock_response`）
- **API 超时**: 前端设置 60 秒超时（AI 分析可能需要较长时间）
- **LLM 日志**: 每次调用记录到 `backend/logs/llm/`，便于调试
- **参考项目**: `MiroFish/` 目录包含向量搜索和实体抽取的参考实现（独立项目，不要修改）
- **无测试文件**: 无测试文件存在 — 前端运行 `npm run lint` 检查，后端无测试运行器配置
- **Git 忽略**: `.env`、`*.db`、`node_modules/`、`__pycache__/`、`.next/` 已被忽略

## Cursor / Copilot 规则

未找到 `.cursorrules`、`.cursor/rules/` 或 `.github/copilot-instructions.md` 文件。已有的 `frontend/AGENTS.md` 仅包含 Next.js 版本警告 — 该文件仅针对前端子目录。
