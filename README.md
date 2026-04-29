# AI 小说创作助手

一个基于 AI 的长篇小说创作辅助平台，通过 Web 界面提供人物关系图、情节关联图、灵感提示、向量语义搜索、知识图谱、角色对话、章节管理、世界观构建、伏笔追踪、角色成长弧线、节奏张力分析和大纲管理等功能。

## 功能特点

### 文件管理
- **文件夹导入**: 选择文件夹自动导入小说内容，一个文件夹对应一部小说
- **多格式支持**: 支持 TXT、MD 文件导入
- **导出功能**: 支持小说内容导出

### 人物系统
- **AI 人物分析**: 全量/增量两种模式，Map-Reduce 架构处理百万字级文本
- **人物关系图**: 自动生成人物关系网络（@xyflow/react），支持拖拽、缩放、编辑
- **角色对话**: 基于角色画像的个性化 AI 对话模拟
- **角色成长弧线**: 追踪角色在各章节的心理、情感、能力变化
- **人物快速搜索**: Ctrl+K 全局快速定位角色

### 情节与结构
- **情节关联图**: AI 分析小说情节，生成节点和因果/伏笔/闪回连接
- **灵感提示**: 基于人物和情节数据，提供场景、情节延续、角色发展、情绪渲染等灵感
- **大纲管理**: 层级化大纲编辑与 AI 辅助生成
- **节奏张力曲线**: 可视化分析故事节奏和张力的起伏变化

### 知识与搜索
- **向量语义搜索**: 基于 Qdrant + sentence-transformers 的语义搜索
- **知识图谱**: GraphRAG 自动抽取实体与关系，构建小说知识图谱
- **世界观构建**: 地点、物品、组织、概念等世界元素管理

### 写作辅助
- **章节管理**: 自动拆分章节，按章节浏览内容
- **伏笔追踪**: 追踪伏笔的埋设与回收状态
- **AI 智能助手**: 情节预测、写作建议、深度一致性检查

## 技术栈

### 前端
- **框架**: Next.js 16.2 + React 19.2 + TypeScript 5
- **UI 组件**: shadcn/ui 4.1 + Tailwind CSS 4 + Radix UI
- **图谱可视化**: @xyflow/react 12（人物关系图/情节关联图）
- **状态管理**: Zustand 5（11 个独立 Store）
- **其他**: Axios、React Markdown、Sonner、Lucide Icons

### 后端
- **框架**: FastAPI 0.115 + Uvicorn（Python 3.12+）
- **ORM**: SQLAlchemy 2.0 + Pydantic 2.11
- **数据库**: SQLite（主存储）+ Neo4j 5（图数据库）+ Qdrant（向量数据库）
- **AI**: DeepSeek API（OpenAI SDK 兼容），支持思考模式（reasoning_effort）
- **Embedding**: sentence-transformers（本地）或云端 API
- **文本处理**: Map-Reduce 分块分析，支持百万字级长文本

## 项目结构

```
xiaoshuo/
├── frontend/                    # Next.js 前端应用
│   ├── src/
│   │   ├── app/                 # 页面入口 (page.tsx)
│   │   ├── components/          # React 组件（15 个模块）
│   │   │   ├── CharacterGraph/      # 人物关系图
│   │   │   ├── PlotGraph/           # 情节关联图
│   │   │   ├── InspirationPanel/    # 灵感面板
│   │   │   ├── VectorSearch/        # 向量语义搜索
│   │   │   ├── KnowledgeGraph/      # 知识图谱
│   │   │   ├── CharacterChat/       # 角色对话
│   │   │   ├── AIAssistant/         # AI 智能助手
│   │   │   ├── CharacterQuickSearch/ # 人物快速搜索
│   │   │   ├── WorldBuilding/       # 世界观构建
│   │   │   ├── ForeshadowTracker/   # 伏笔追踪
│   │   │   ├── CharacterArc/        # 角色成长弧线
│   │   │   ├── TensionCurve/        # 节奏张力曲线
│   │   │   ├── OutlineWorkflow/     # 大纲管理
│   │   │   ├── Layout/              # 布局组件
│   │   │   └── ui/                  # shadcn/ui 基础组件
│   │   ├── stores/              # Zustand 状态管理（11 个 Store）
│   │   ├── types/               # TypeScript 类型定义
│   │   └── lib/                 # 工具函数与 API 客户端
│   └── package.json
│
├── backend/                     # FastAPI 后端
│   ├── app/
│   │   ├── api/                 # API 路由层（16 个模块）
│   │   │   ├── files.py             # 文件/小说管理
│   │   │   ├── characters.py        # 人物/关系管理
│   │   │   ├── plots.py             # 情节/连接管理
│   │   │   ├── inspiration.py       # 灵感生成
│   │   │   ├── search.py            # 向量搜索
│   │   │   ├── graph.py             # 知识图谱
│   │   │   ├── chat.py              # 角色对话
│   │   │   ├── assistant.py         # AI 助手
│   │   │   ├── analysis.py          # 异步分析任务
│   │   │   ├── chapters.py          # 章节管理
│   │   │   ├── worldbuilding.py     # 世界观构建
│   │   │   ├── foreshadows.py       # 伏笔追踪
│   │   │   ├── character_arcs.py    # 角色成长弧线
│   │   │   ├── tension.py           # 节奏张力分析
│   │   │   └── outlines.py          # 大纲管理
│   │   ├── services/            # 业务逻辑层
│   │   │   ├── character_analyzer.py    # 人物分析
│   │   │   ├── plot_analyzer.py         # 情节分析
│   │   │   ├── map_reduce_analyzer.py   # Map-Reduce 框架
│   │   │   ├── chapter_splitter.py      # 章节拆分
│   │   │   ├── character_arc_analyzer.py # 角色弧线分析
│   │   │   ├── tension_analyzer.py      # 张力分析
│   │   │   ├── foreshadow_tracker.py    # 伏笔追踪
│   │   │   ├── outline_service.py       # 大纲服务
│   │   │   ├── inspiration_gen.py       # 灵感生成
│   │   │   ├── analyzers/               # 分块分析器（Mapper/Reducer）
│   │   │   ├── vector/                  # 向量搜索服务
│   │   │   ├── graph_rag/               # GraphRAG 知识图谱
│   │   │   ├── character_chat/          # 角色对话系统
│   │   │   └── novel_assistant/         # AI 助手（情节预测/写作建议）
│   │   ├── agent/               # AI 客户端（OpenAI SDK → DeepSeek）
│   │   ├── db/                  # 数据访问层（Neo4j + SQLite Repository）
│   │   ├── models/              # SQLAlchemy 数据模型
│   │   ├── core/                # 配置、异常处理、日志、JSON 工具
│   │   └── main.py              # FastAPI 入口
│   ├── data/novels/             # 小说存储目录
│   └── requirements.txt
│
├── docker-compose.yml           # Docker 编排（Qdrant + Neo4j + 前后端）
├── CLAUDE.md                    # Claude Code 项目指引
└── README.md
```

## 快速开始

### 环境要求
- Node.js 18+
- Python 3.12+
- Docker（可选，用于 Qdrant 和 Neo4j）

### 1. 启动数据库（Docker）
```bash
docker run -d --name qdrant -p 6333:6333 -v qdrant_data:/qdrant/storage --restart unless-stopped qdrant/qdrant:latest
docker run -d --name neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password -e NEO4J_PLUGINS='["apoc"]' -v neo4j_data:/data --restart unless-stopped neo4j:5
```

### 2. 启动后端
```bash
cd backend
pip install -r requirements.txt

# 配置 AI 密钥
cp .env.example .env  # 编辑 .env 填入 DEEPSEEK_API_KEY

python -m uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

### 3. 启动前端
```bash
cd frontend
npm install
npm run dev
```

### 访问地址
- 前端: http://localhost:3000
- 后端 API: http://localhost:8002
- API 文档: http://localhost:8002/docs
- Neo4j 控制台: http://localhost:7474
- Qdrant 控制台: http://localhost:6333/dashboard

### Docker 一键部署
```bash
docker compose up -d
```

## 环境配置

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
```

> 未配置 `DEEPSEEK_API_KEY` 时会使用 Mock 数据，便于前端开发测试。

## 使用说明

1. **打开文件夹**: 点击左侧"打开文件夹"，选择包含小说 TXT/MD 文件的文件夹
2. **选择小说**: 在侧边栏选择要分析的小说
3. **分析人物**: 切换到"人物关系图"标签，点击"AI 分析"（支持全量/增量模式）
4. **分析情节**: 切换到"情节关联图"标签，点击"AI 分析"
5. **获取灵感**: 切换到"灵感提示"标签，选择类型后生成
6. **语义搜索**: 切换到"向量搜索"标签，输入自然语言查询小说内容
7. **角色对话**: 切换到"角色对话"标签，选择人物进行对话模拟
8. **快捷搜索**: 随时按 Ctrl+K 快速搜索人物

## API 接口

### 文件管理
- `GET /api/files/novels` - 获取小说列表
- `POST /api/files/upload-folder` - 上传文件夹内容
- `POST /api/files/scan?path=xxx` - 扫描本地文件夹
- `DELETE /api/files/novels/{id}` - 删除小说

### 人物与关系
- `GET /api/characters?novel_id=xxx` - 获取人物列表
- `POST /api/characters/analyze?novel_id=xxx&mode=full|incremental` - AI 分析人物
- `POST /api/characters/analyze/stream?novel_id=xxx` - SSE 流式分析人物
- `PUT /api/characters/{id}` - 更新人物信息
- `DELETE /api/characters/{id}` - 删除人物
- `POST /api/characters/relations/analyze?novel_id=xxx` - AI 分析人物关系

### 情节管理
- `GET /api/plots?novel_id=xxx` - 获取情节节点
- `POST /api/plots/analyze?novel_id=xxx` - AI 分析情节
- `POST /api/plots/connections/analyze?novel_id=xxx` - AI 分析情节关联

### 搜索与图谱
- `POST /api/search/vector` - 向量语义搜索
- `POST /api/graph/build` - 构建知识图谱
- `GET /api/graph/entities?novel_id=xxx` - 获取图谱实体

### 创作辅助
- `POST /api/inspiration/{type}` - 生成灵感（plot/character/emotion/scene）
- `POST /api/chat/session` - 创建角色对话会话
- `POST /api/assistant/predict` - 情节预测
- `GET /api/chapters?novel_id=xxx` - 章节列表
- `GET /api/outlines?novel_id=xxx` - 大纲数据

## 许可证

MIT License
