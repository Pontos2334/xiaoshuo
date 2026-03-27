# 小说创作助手

一个基于AI的小说创作辅助工具，通过Web界面提供人物关系图、情节关联图和灵感提示功能。

## 功能特点

### 核心功能
- **文件夹导入**: 选择文件夹自动导入小说内容，一个文件夹对应一部小说
- **人物关系图**: AI分析小说内容，自动生成人物信息和关系网络，支持拖拽、缩放、编辑
- **情节关联图**: AI分析小说情节，生成情节节点和连接关系，支持因果、伏笔、闪回等类型
- **灵感提示**: 基于人物和情节数据，提供写作灵感、情节延续建议、情绪渲染技巧等

### 交互特性
- 可视化图谱支持拖拽、缩放、点击查看详情
- 人物/情节节点支持编辑和删除
- 全局加载状态和操作反馈提示
- 中文界面

## 技术栈

### 前端
- **框架**: Next.js 16 + React 19
- **UI组件**: shadcn/ui + Tailwind CSS
- **图谱可视化**: AntV G6 v5 (人物关系图) + @xyflow/react (情节关联图)
- **状态管理**: Zustand
- **语言**: TypeScript

### 后端
- **框架**: FastAPI (Python)
- **数据库**: SQLAlchemy + SQLite
- **AI能力**: 智谱AI GLM-5 (通过Anthropic兼容API)

## 项目结构

```
xiaoshuo/
├── frontend/               # Next.js前端应用
│   ├── src/
│   │   ├── app/            # 页面入口
│   │   ├── components/     # React组件
│   │   │   ├── CharacterGraph/  # 人物关系图
│   │   │   ├── PlotGraph/       # 情节关联图
│   │   │   ├── InspirationPanel/ # 灵感面板
│   │   │   ├── Layout/          # 布局组件
│   │   │   └── ui/              # UI基础组件
│   │   ├── stores/         # Zustand状态管理
│   │   ├── types/          # TypeScript类型定义
│   │   └── lib/            # 工具函数
│   └── package.json
│
├── backend/                # FastAPI后端
│   ├── app/
│   │   ├── api/            # API路由
│   │   │   ├── characters.py  # 人物API
│   │   │   ├── plots.py       # 情节API
│   │   │   ├── files.py       # 文件API
│   │   │   └── inspiration.py # 灵感API
│   │   ├── services/       # 业务逻辑
│   │   │   ├── character_analyzer.py
│   │   │   ├── plot_analyzer.py
│   │   │   └── inspiration_gen.py
│   │   ├── models/         # 数据模型
│   │   ├── agent/          # Claude Agent客户端
│   │   └── main.py         # 应用入口
│   ├── data/novels/        # 小说存储目录
│   └── requirements.txt
│
├── data/                   # 示例数据
│   └── novels/
│
├── README.md
├── install.bat             # Windows安装脚本
└── start.bat               # Windows启动脚本
```

## 快速开始

### 环境要求
- Node.js 18+
- Python 3.10+
- npm

### 一键启动 (Windows)
```bash
# 双击运行
install.bat    # 安装所有依赖
start.bat      # 启动前后端服务
```

### 手动安装

#### 后端
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

#### 前端
```bash
cd frontend
npm install
npm run dev
```

### 访问地址
- 前端: http://localhost:3000
- 后端API: http://localhost:8002
- API文档: http://localhost:8002/docs

## AI配置

项目使用智谱AI (GLM-5) 模型，配置文件位于 `backend/.env`：

```env
ANTHROPIC_API_KEY=your_api_key
ANTHROPIC_BASE_URL=https://open.bigmodel.cn/api/anthropic
CLAUDE_MODEL=glm-5
MAX_TOKENS=4096
DATABASE_URL=sqlite:///./novel_assistant.db
```

## 使用说明

1. **打开文件夹**: 点击右上角"打开文件夹"，选择包含小说TXT/MD文件的文件夹
2. **选择小说**: 在左侧边栏选择要分析的小说
3. **分析人物**: 切换到"人物关系图"标签，点击"AI分析"
4. **分析情节**: 切换到"情节关联图"标签，点击"AI分析"
5. **获取灵感**: 切换到"灵感提示"标签，选择类型后生成

## API接口

### 文件相关
- `GET /api/files/novels` - 获取小说列表
- `POST /api/files/upload-folder` - 上传文件夹内容
- `POST /api/files/scan?path=xxx` - 扫描本地文件夹

### 人物相关
- `GET /api/characters?novel_id=xxx` - 获取人物列表
- `POST /api/characters/analyze?novel_id=xxx` - AI分析人物
- `PUT /api/characters/{id}` - 更新人物信息
- `DELETE /api/characters/{id}` - 删除人物
- `POST /api/characters/relations/analyze?novel_id=xxx` - AI分析人物关系

### 情节相关
- `GET /api/plots?novel_id=xxx` - 获取情节节点
- `POST /api/plots/analyze?novel_id=xxx` - AI分析情节
- `PUT /api/plots/{id}` - 更新情节信息
- `POST /api/plots/connections/analyze?novel_id=xxx` - AI分析情节关联

### 灵感相关
- `POST /api/inspiration/plot` - 情节灵感
- `POST /api/inspiration/continue` - 情节延续建议
- `POST /api/inspiration/character` - 角色发展建议
- `POST /api/inspiration/emotion` - 情绪渲染建议

## 开发状态

### 已完成
- [x] 前后端基础架构
- [x] 文件夹导入功能
- [x] 人物关系图可视化
- [x] 情节关联图可视化
- [x] AI分析接口
- [x] 灵感生成功能
- [x] 中文界面
- [x] 加载状态反馈

### 待开发
- [ ] 支持更多文件格式 (DOCX, PDF)
- [ ] 小说大纲编辑器
- [ ] 数据导出功能
- [ ] 多设备同步

## 许可证

MIT License
