# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

AI小说创作助手 - 通过Web界面提供人物关系图、情节关联图和灵感提示功能。

## 常用命令

### 启动开发环境
```bash
# 后端 (在 backend/ 目录)
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload

# 前端 (在 frontend/ 目录)
npm install
npm run dev
```

### 访问地址
- 前端: http://localhost:3000
- 后端API: http://localhost:8002
- API文档: http://localhost:8002/docs

## 架构

### 前后端分离
- **前端**: Next.js + React + TypeScript，端口 3000
- **后端**: FastAPI + SQLite，端口 8002

### 前端架构
- `src/stores/` - Zustand 状态管理（Novel, Character, Plot, Inspiration, UI 五个独立 store）
- `src/lib/api.ts` - Axios API 客户端封装
- `src/components/CharacterGraph/` - 人物关系图（AntV G6 v5）
- `src/components/PlotGraph/` - 情节关联图（React Flow）
- `src/components/InspirationPanel/` - 灵感面板

### 后端架构
- `app/main.py` - FastAPI 入口，CORS 已配置允许 localhost:3000
- `app/api/` - API 路由（files, characters, plots, inspiration）
- `app/services/` - 业务逻辑层（character_analyzer, plot_analyzer, inspiration_gen）
- `app/agent/client.py` - AI 客户端，使用 Anthropic 兼容 API
- `app/models/` - SQLAlchemy 数据模型

### AI 配置
后端通过 `backend/.env` 配置：
```
ANTHROPIC_API_KEY=your_key
ANTHROPIC_BASE_URL=https://open.bigmodel.cn/api/anthropic
CLAUDE_MODEL=glm-5
```

## 注意事项

- 前端使用 Next.js 16，部分 API 与训练数据中的版本不同，开发前参考 `frontend/node_modules/next/dist/docs/`
- 后端无 API Key 时会返回 mock 数据，便于前端开发测试
