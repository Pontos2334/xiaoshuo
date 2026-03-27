# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

AI小说创作助手 - 通过Web界面提供人物关系图、情节关联图、灵感提示、向量搜索、知识图谱和人物对话功能。

## 常用命令

### 后端 (在 backend/ 目录)
```bash
pip install -r requirements.txt          # 安装依赖
python -m uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload  # 启动开发服务
```

### 前端 (在 frontend/ 目录)
```bash
npm install                              # 安装依赖
npm run dev                              # 启动开发服务
npm run build                            # 构建生产版本
npm run lint                             # 运行 ESLint 检查
```

### Docker Compose
```bash
docker-compose up -d                     # 启动 Qdrant + Neo4j + 前后端服务
```

### 访问地址
- 前端: http://localhost:3000
- 后端API: http://localhost:8002
- API文档: http://localhost:8002/docs
- Neo4j控制台: http://localhost:7474
- Qdrant控制台: http://localhost:6333/dashboard

## 架构

### 前后端分离
- **前端**: Next.js 16.2 + React 19.2 + TypeScript，端口 3000
- **后端**: FastAPI + SQLite + Neo4j + Qdrant，端口 8002

### 前端架构
- `src/stores/index.ts` - Zustand 状态管理（Novel, Character, Plot, Inspiration, UI 五个独立 store）
- `src/lib/api.ts` - Axios API 客户端封装，60秒超时
- `src/components/CharacterGraph/` - 人物关系图（AntV G6 v5）
- `src/components/PlotGraph/` - 情节关联图（@xyflow/react v12）
- `src/components/InspirationPanel/` - 灵感面板

### 后端架构
```
backend/app/
├── main.py              # FastAPI 入口，注册所有路由
├── core/
│   ├── config.py        # Pydantic Settings 配置管理
│   ├── exceptions.py    # 全局异常处理
│   └── logging_config.py # 日志配置
├── api/                 # API 路由层
│   ├── files.py         # 文件/小说管理
│   ├── characters.py    # 人物/关系管理
│   ├── plots.py         # 情节/连接管理
│   ├── inspiration.py   # 灵感生成
│   ├── search.py        # 向量搜索
│   ├── graph.py         # 知识图谱
│   ├── chat.py          # 人物对话
│   ├── assistant.py     # 智能助手
│   └── analysis.py      # 长文本分析任务
├── services/            # 业务逻辑层
│   ├── character_analyzer.py
│   ├── plot_analyzer.py
│   ├── inspiration_gen.py
│   ├── text_chunker.py          # 文本分块
│   ├── map_reduce_analyzer.py   # Map-Reduce 分析
│   ├── analyzers/               # 分块分析器
│   ├── vector/          # 向量搜索服务
│   │   ├── embedding_service.py
│   │   └── qdrant_service.py
│   ├── graph_rag/       # GraphRAG 知识图谱
│   ├── character_chat/  # 人物对话系统
│   └── novel_assistant/ # 智能助手
├── agent/client.py      # AI 客户端（Anthropic 兼容 API）
├── db/neo4j_client.py   # Neo4j 图数据库客户端
└── models/              # SQLAlchemy 数据模型
```

### 关键数据流
1. **小说导入**: 文件夹扫描 → 存储到 `backend/data/novels/` → SQLite 记录元信息
2. **AI分析**: 读取小说文本 → ClaudeAgentClient 调用 LLM → 解析 JSON 响应 → 存入 SQLite/Neo4j
3. **图谱可视化**: 前端调用 API → SQLite 查询 → 转换为 G6/ReactFlow 数据格式
4. **向量搜索**: 文本 → embedding_service 编码 → Qdrant 存储/检索

### 环境配置
后端通过 `backend/.env` 配置：
```env
# AI 配置
ANTHROPIC_API_KEY=your_key
ANTHROPIC_BASE_URL=https://open.bigmodel.cn/api/anthropic
CLAUDE_MODEL=glm-5
MAX_TOKENS=4096

# 数据库
DATABASE_URL=sqlite:///./novel_assistant.db
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# 向量搜索
QDRANT_URL=http://localhost:6333
EMBEDDING_USE_LOCAL=true
EMBEDDING_LOCAL_MODEL=paraphrase-multilingual-MiniLM-L12-v2

# GraphRAG
GRAPH_RAG_MAX_GLEANINGS=1
```

## 重要注意事项

- **Next.js 16**: 与训练数据中的版本有 breaking changes，开发前参考 `frontend/node_modules/next/dist/docs/`
- **React 19**: 使用 React 19.2.4，注意与旧版 API 的差异
- **Mock 数据**: 后端无 API Key 时会返回 mock 数据（见 `agent/client.py:_mock_response`），便于前端开发测试
- **API 超时**: 前端设置 60 秒超时，因为 AI 分析可能需要较长时间
- **LLM 日志**: 每次调用记录到 `backend/logs/llm/`，便于调试
- **参考项目**: `MiroFish/` 目录包含向量搜索和实体抽取的参考实现
