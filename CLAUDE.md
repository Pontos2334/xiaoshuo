# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

AI小说创作助手 - 通过Web界面提供人物关系图、情节关联图、灵感提示、向量搜索、知识图谱、人物对话、章节管理、世界观构建、伏笔追踪、角色成长弧线、节奏张力分析和大纲管理功能。

## 常用命令

### 后端 (在 backend/ 目录)
```bash
pip install -r requirements.txt          # 安装依赖
python -m uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload  # 启动开发服务
```

### 前端 (在 frontend/ 目录)
```bash
npm install                              # 安装依赖
npm run dev                              # 启动开发服务 (Turbopack)
npm run build                            # 构建生产版本
npm run lint                             # 运行 ESLint 检查
```

### Docker 启动数据库
```bash
# 手动启动 Qdrant + Neo4j（前后端本地开发时推荐）
docker run -d --name qdrant -p 6333:6333 -p 6334:6334 -v qdrant_data:/qdrant/storage --restart unless-stopped qdrant/qdrant:v1.12.4
docker run -d --name neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password -e NEO4J_PLUGINS='["apoc"]' -v neo4j_data:/data -v neo4j_logs:/logs --restart unless-stopped neo4j:latest
```

### 访问地址
- 前端: http://localhost:3000
- 后端API: http://localhost:8002
- API文档: http://localhost:8002/docs
- Neo4j控制台: http://localhost:7474
- Qdrant控制台: http://localhost:6333/dashboard

## 架构

### 前后端分离
- **前端**: Next.js 16.2.1 + React 19.2.4 + TypeScript + Zustand + Tailwind CSS，端口 3000
- **后端**: FastAPI + SQLite + Neo4j + Qdrant，端口 8002

### 前端架构
- `src/stores/index.ts` - Zustand 状态管理，11 个独立 store：
  Novel, Character, Plot, Inspiration, UI, Chapter, WorldBuilding, Foreshadow, CharacterArc, Tension, Outline
- `src/lib/api.ts` - Axios API 客户端封装，60秒超时
- `src/components/CharacterGraph/` - 人物关系图（AntV G6 v5）
- `src/components/PlotGraph/` - 情节关联图（@xyflow/react v12）
- `src/components/InspirationPanel/` - 灵感面板
- `src/components/ChapterNav/` - 章节导航
- `src/components/WorldBuilding/` - 世界观构建
- `src/components/ForeshadowTracker/` - 伏笔追踪
- `src/components/CharacterArc/` - 角色成长弧线
- `src/components/TensionCurve/` - 节奏张力曲线
- `src/components/OutlineWorkflow/` - 大纲管理工作流
- `src/components/VectorSearch/` - 向量语义搜索
- `src/components/KnowledgeGraph/` - 知识图谱
- `src/components/CharacterChat/` - 人物对话
- `src/components/AIAssistant/` - AI 智能助手
- `src/components/CharacterQuickSearch/` - 人物快速搜索
- `src/components/ui/` - 通用 UI 组件（shadcn/ui）

### 后端架构
```
backend/app/
├── main.py              # FastAPI 入口，注册 16 个路由模块
├── core/
│   ├── config.py        # Pydantic Settings 配置管理
│   ├── exceptions.py    # 全局异常处理
│   └── logging_config.py # 日志配置
├── api/                 # API 路由层（16 个模块）
│   ├── files.py         # 文件/小说管理
│   ├── characters.py    # 人物/关系管理
│   ├── plots.py         # 情节/连接管理
│   ├── inspiration.py   # 灵感生成
│   ├── search.py        # 向量搜索
│   ├── graph.py         # 知识图谱
│   ├── chat.py          # 人物对话
│   ├── assistant.py     # 智能助手
│   ├── analysis.py      # 长文本分析任务
│   ├── chapters.py      # 章节管理
│   ├── worldbuilding.py # 世界观构建
│   ├── foreshadows.py   # 伏笔追踪
│   ├── character_arcs.py # 角色成长弧线
│   ├── tension.py       # 节奏张力分析
│   └── outlines.py      # 大纲管理
├── services/            # 业务逻辑层
│   ├── character_analyzer.py    # 人物分析
│   ├── plot_analyzer.py         # 情节分析
│   ├── inspiration_gen.py       # 灵感生成
│   ├── text_chunker.py          # 文本分块
│   ├── map_reduce_analyzer.py   # Map-Reduce 分析
│   ├── chapter_splitter.py      # 章节自动拆分
│   ├── character_arc_analyzer.py # 角色成长弧线分析
│   ├── tension_analyzer.py      # 节奏张力分析
│   ├── foreshadow_tracker.py    # 伏笔追踪
│   ├── outline_service.py       # 大纲管理服务
│   ├── creative_helper.py       # 创意辅助
│   ├── deep_consistency_checker.py # 深度一致性检查
│   ├── analyzers/               # 分块分析器
│   ├── vector/                  # 向量搜索服务
│   │   ├── embedding_service.py
│   │   └── qdrant_service.py
│   ├── graph_rag/               # GraphRAG 知识图谱
│   ├── character_chat/          # 人物对话系统
│   └── novel_assistant/         # 智能助手（情节预测、写作建议）
├── agent/
│   ├── client.py        # AI 客户端（OpenAI SDK → DeepSeek）
│   └── llm_client.py    # LLM 客户端工厂（单例模式）
├── db/
│   ├── neo4j_client.py  # Neo4j 图数据库客户端
│   └── repository.py    # SQLite 数据访问层
└── models/              # SQLAlchemy 数据模型
```

### 关键数据流
1. **小说导入**: 文件夹扫描 → 存储到 `backend/data/novels/` → SQLite 记录元信息
2. **AI分析**: 读取小说文本 → AIAgentClient (OpenAI SDK) 调用 DeepSeek → 解析 JSON 响应 → 存入 SQLite/Neo4j
3. **图谱可视化**: 前端调用 API → SQLite 查询 → 转换为 G6/ReactFlow 数据格式
4. **向量搜索**: 文本 → embedding_service 编码 → Qdrant 存储/检索

### 环境配置
后端通过 `backend/.env` 配置：
```env
# AI 配置 (DeepSeek - OpenAI SDK 兼容)
DEEPSEEK_API_KEY=sk-xxxxxxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
MAX_TOKENS=4096
DEEPSEEK_REASONING_EFFORT=max

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

- **AI 服务**: 使用 DeepSeek API（OpenAI SDK 兼容模式），通过 `openai.OpenAI` 客户端调用。已默认开启思考模式（`reasoning_effort="max"` + `thinking: {type: "enabled"}`），模型输出时会先进行思维链推理，`reasoning_content` 会记录到日志中。配置字段为 `DEEPSEEK_*` 前缀。注意：思考模式下 `temperature`/`top_p` 等参数不会生效
- **Next.js 16**: 与训练数据中的版本有 breaking changes，开发前参考 `frontend/node_modules/next/dist/docs/`
- **React 19**: 使用 React 19.2.4，注意与旧版 API 的差异
- **Mock 数据**: 后端无 `DEEPSEEK_API_KEY` 时会返回 mock 数据（见 `agent/client.py:_mock_response`），便于前端开发测试
- **API 超时**: 前端设置 60 秒超时，因为 AI 分析可能需要较长时间
- **LLM 日志**: 每次调用记录到 `backend/logs/llm/`，便于调试
- **Python 版本**: 使用 Python 3.14 时注意 pydantic-core 编译兼容性问题，可设置 `PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1` 或使用 Python 3.12/3.13
- **Neo4j 版本**: Docker 运行时使用 `neo4j:latest` (2026.02.3+)，注意 `dbms.memory.heap.*` 配置项已更名为 `server.memory.heap.*`
- **参考项目**: `MiroFish/` 目录包含向量搜索和实体抽取的参考实现
