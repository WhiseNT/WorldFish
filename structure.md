# WorldFish 项目架构文档

## 1. 项目概述

**WorldFish** (原名 MiroFish) 是一个基于多智能体技术的世界观模拟推演引擎，专为创作者设计。它允许用户输入世界观设定、年代大事记、人物信息等数据，自动构建高保真数字世界，通过数千个智能体交互进行社会演化推演，最终生成详细的推演报告。

- **目标用户**: 小说作家、游戏设计师、历史研究者、决策者
- **开源协议**: AGPL-3.0
- **技术栈**: Vue 3 (前端) + Flask (后端) + LLM API (OpenAI SDK 格式) + Zep Cloud (记忆图谱)

---

## 2. 目录结构

```
WorldFish/
├── frontend/                   # Vue 3 前端应用
│   ├── src/
│   │   ├── api/                # API 请求封装层
│   │   │   ├── index.js        # Axios 实例 + 拦截器 + 重试机制
│   │   │   ├── graph.js        # 图谱相关 API
│   │   │   ├── project.js      # 项目管理 API
│   │   │   ├── report.js       # 报告生成 API
│   │   │   ├── simulation.js   # 模拟运行 API
│   │   │   └── world.js        # 世界观构建 API
│   │   ├── components/         # 通用组件
│   │   │   ├── AppLayout.vue   # 应用外壳布局（导航栏 + 内容区）
│   │   │   ├── GraphPanel.vue  # D3.js 知识图谱可视化面板
│   │   │   ├── LanguageSwitcher.vue  # 语言切换组件
│   │   │   └── StepIndicator.vue     # 步骤指示器
│   │   ├── views/              # 页面视图
│   │   │   ├── Home.vue               # 首页/项目列表
│   │   │   ├── WorldBuilderView.vue   # 世界观构建页
│   │   │   ├── SimulationSetup.vue    # 推演设置页
│   │   │   └── SimulationEvolution.vue # 推演进化展示页
│   │   ├── router/index.js     # Vue Router 路由配置
│   │   ├── i18n/index.js       # Vue I18n 国际化
│   │   ├── main.js             # 应用入口
│   │   └── App.vue             # 根组件
│   ├── vite.config.js
│   └── package.json            # Vue 3, D3.js, Vue Router, Vue I18n, Axios
│
├── backend/                    # Flask 后端服务
│   ├── app/
│   │   ├── __init__.py         # Flask 应用工厂 (create_app)，注册蓝图和CORS
│   │   ├── config.py           # 全局配置 (LLM/Zep/OASIS/文件上传参数)
│   │   ├── api/                # REST API 路由层 (Flask Blueprints)
│   │   │   ├── __init__.py     # 蓝图声明
│   │   │   ├── world_build.py  # 世界观 CRUD + AI 提取
│   │   │   ├── graph.py        # 本体生成 + 图谱构建 (Zep/Local)
│   │   │   ├── project.py      # 项目 CRUD
│   │   │   ├── simulation.py   # 实体读取 + Profile生成 + 模拟管理 + Interview
│   │   │   ├── evolution.py    # 世界观进化推演 (LLM驱动)
│   │   │   └── report.py       # 报告生成 + 聊天
│   │   ├── models/             # 数据模型 + 文件持久化仓库
│   │   │   ├── __init__.py
│   │   │   ├── world.py        # WorldSetting, Entity, Event, WorldManager
│   │   │   ├── project.py      # Project, ProjectStatus, ProjectManager
│   │   │   ├── evolution.py    # Evolution, EvolutionRound, EvolutionManager
│   │   │   └── task.py         # Task, TaskStatus, TaskManager (异步任务管理)
│   │   ├── services/           # 核心业务逻辑层
│   │   │   ├── world_extractor.py           # 基础世界观提取（LLM）
│   │   │   ├── enhanced_world_extractor.py  # 增强提取（章节感知+并行细粒度）
│   │   │   ├── text_processor.py            # 文本切块处理
│   │   │   ├── ontology_generator.py        # 本体定义生成（LLM设计实体/关系类型）
│   │   │   ├── graph_builder.py             # Zep Cloud 图谱构建（异步）
│   │   │   ├── local_graph_builder.py       # 本地图谱构建（无需Zep）
│   │   │   ├── zep_entity_reader.py         # Zep图谱实体读取与过滤
│   │   │   ├── oasis_profile_generator.py   # Agent Profile生成（图谱→OASIS人设）
│   │   │   ├── simulation_config_generator.py # 模拟配置参数生成
│   │   │   ├── simulation_manager.py        # 模拟状态管理器
│   │   │   ├── simulation_runner.py         # 模拟运行器（子进程管理+动作记录）
│   │   │   ├── simulation_ipc.py            # 模拟进程间通信
│   │   │   ├── world_evolution_engine.py    # LLM世界观进化引擎（规划→推演→整合）
│   │   │   ├── zep_graph_memory_updater.py  # 模拟后图谱更新
│   │   │   ├── report_agent.py              # Report Agent（ReACT模式报告生成+对话）
│   │   │   ├── zep_tools.py                 # Zep检索工具集（搜索/节点/边查询）
│   │   │   └── timeline_manager.py          # 时间线管理
│   │   └── utils/             # 工具函数
│   │       ├── llm_client.py   # LLM客户端（OpenAI SDK封装）
│   │       ├── file_parser.py  # 文件解析（PDF/MD/TXT，多编码回退）
│   │       ├── logger.py       # 日志系统
│   │       ├── locale.py       # 国际化（请求头/线程本地）
│   │       ├── zep_paging.py   # Zep分页工具
│   │       └── retry.py        # 重试工具
│   ├── scripts/                # 独立脚本
│   │   ├── run_parallel_simulation.py
│   │   ├── run_reddit_simulation.py
│   │   ├── run_twitter_simulation.py
│   │   └── action_logger.py
│   ├── uploads/                # 上传文件 + 持久化数据目录
│   │   ├── worlds/             # 世界观 JSON
│   │   ├── projects/           # 项目文件 + extracted_text
│   │   ├── evolutions/         # 推演结果 JSON
│   │   ├── graphs/             # 本地图谱 JSON
│   │   ├── simulations/        # OASIS 模拟输出
│   │   └── reports/            # 生成的报告
│   ├── logs/                   # 日志文件
│   ├── run.py                  # 启动入口
│   ├── pyproject.toml          # Python 项目配置 (uv)
│   └── requirements.txt        # pip 依赖
│
├── static/image/               # 静态图片资源（Logo、截图、封面）
├── locales/                    # 前端/后端共享的翻译文件
│   ├── zh.json, en.json, ...   # 各语言翻译
│   └── languages.json          # 语言注册表
├── .claude/                    # Claude AI 配置
├── .github/workflows/          # CI/CD (Docker 镜像构建)
├── docker-compose.yml          # Docker 部署配置
├── Dockerfile                  # 容器镜像定义
├── package.json                # 根项目脚本 (npm run dev/setup)
├── .env.example                # 环境变量模板
├── DESIGN_DOCUMENT.md          # 详细设计文档 (中文)
├── design-philosophy.md        # 设计哲学: "Calm Tech Minimalism"
├── README.md                   # 项目说明 (英文)
├── README-ZH.md                # 项目说明 (中文)
└── WORLDBUILDING_LLM_GUIDE.md  # LLM世界构建指南
```

### RAG 系统 (新增)

```
backend/app/
├── services/rag_service.py     # ChromaDB 向量知识库服务 (Embedding: ModelScope Qwen3-Embedding-8B)
├── api/rag.py                  # RAG REST API (/api/{world_id}/rag/*)
├── prompts/                    # 提示词模板目录
│   ├── extraction_system.txt   # 世界观提取系统指令
│   ├── extraction_chunk.txt    # 分块提取模板
│   ├── consolidation.txt       # 整合合并模板
│   ├── writing_style.txt       # 文风分析模板
│   └── validation.txt          # 质量验证模板
frontend/src/
├── api/rag.js                  # RAG 前端 API 调用
└── views/RagView.vue           # RAG 独立标签页（文档管理 + 语义检索）

.env 配置:
  EMBEDDING_API_KEY=ms-xxx      # ModelScope API Key（独立于 LLM）
  EMBEDDING_BASE_URL=https://api-inference.modelscope.cn/v1
  EMBEDDING_MODEL_NAME=Qwen/Qwen3-Embedding-8B
  RAG_CHUNK_SIZE=800            # 文本切块大小（字符）
  RAG_TOP_K=5                   # 检索返回条数
```

---

## 3. 核心工作流 (Pipeline)

用户操作的主线流程如下：

```
[1] 世界观构建        [2] 图谱构建          [3] 模拟/推演       [4] 报告生成
  WorldBuilder ──────> Graph Builder ──────> Simulation ──────> Report
      │                     │                │   │                 │
      │ 上传文本/手动输入    │ 本体生成        │   │ OASIS社交模拟   │ ReACT Agent
      │ AI提取实体/事件     │ Zep图谱构建     │   │ 或LLM进化推演   │ 多轮反思生成
      │ 文件持久化          │ 异步任务        │   │ 实时监控        │ Zep工具检索
```

### 3.1 世界观构建 (Step 1)

**路由**: `/world-builder`  
**API**: `/api/world/*`

1. 用户创建世界观，输入名称、时代背景、设定等
2. 可选择上传 PDF/MD/TXT 文件 → `EnhancedWorldExtractor` 使用 LLM 并行提取实体、事件、设定
3. 支持手动编辑：添加/修改 Entity（人物、国家、组织等）、Event（事件时间线）、Setting（设定条目）、日历系统、地图数据
4. 持久化到 `uploads/worlds/{world_id}/world.json`

**核心类**:
- `WorldSetting` — 世界观数据模型，含 entities[], events[], settings{}
- `Entity` — 实体（人物/国家/组织/地点/物品/能力），支持多阶段(stages)
- `Event` — 事件，含时间、描述、关联实体
- `EnhancedWorldExtractor` — 章节感知 + 20线程并行 LLM 提取

### 3.2 图谱构建 (Step 2)

**路由**: 从项目创建触发  
**API**: `/api/graph/*`, `/api/project/*`

1. 创建 Project（关联 World 或独立上传文件）
2. `OntologyGenerator` 使用 LLM 分析文本，设计适合社交媒体模拟的实体类型和关系类型
3. 两种图谱构建方式：
   - **Zep Cloud**: `GraphBuilderService` 分块异步构建，支持进度查询
   - **Local**: `LocalGraphBuilder` 本地构建（无需 Zep API Key）
4. 图谱构建后返回 graph_id，可供模拟使用

**核心类**:
- `OntologyGenerator` — LLM 生成本体定义（实体类型 + 关系类型）
- `GraphBuilderService` — Zep API 异步图谱构建
- `LocalGraphBuilder` — 本地JSON图谱构建
- `Project` — 项目模型，状态机: CREATED → ONTOLOGY_GENERATED → GRAPH_BUILDING → GRAPH_COMPLETED

### 3.3 模拟/推演 (Step 3)

WorldFish 提供 **两种并行的推演模式**：

#### A. OASIS 社交媒体模拟 (Simulation)

**API**: `/api/simulation/*`

基于 [OASIS](https://github.com/camel-ai/oasis) 框架的 Twitter + Reddit 双平台并行模拟：

1. 从 Zep 图谱读取实体 → `ZepEntityReader` 过滤有效实体
2. `OasisProfileGenerator` 将实体转为 Agent Profile (人设: bio, persona, MBTI等)
3. `SimulationConfigGenerator` LLM 生成模拟配置参数
4. `SimulationRunner` 启动子进程运行 OASIS 模拟，实时记录每个 Agent 的动作
5. 支持暂停/停止/Interview（与模拟中 Agent 对话）

**平台动作**:
- Twitter: CREATE_POST, LIKE_POST, REPOST, FOLLOW, QUOTE_POST, DO_NOTHING
- Reddit: CREATE_POST, CREATE_COMMENT, LIKE/DISLIKE, SEARCH, FOLLOW, MUTE, etc.

#### B. LLM 世界观进化推演 (Evolution)

**API**: `/api/evolution/*`

纯 LLM 驱动的世界观演进，不依赖 OASIS：

1. 用户设定推演场景 (scenario) 和参数（轮次、温度、时间跨度）
2. `WorldEvolutionEngine` 分阶段执行：**规划 → 分阶段推演 → 整合**
3. 每轮推演生成叙事文本 + 实体状态变更
4. 支持分支推演（从某轮重新推演，生成新分支）
5. 推演完毕后可"变更实体"（将推演结果写回世界观）

**核心类**:
- `SimulationManager` — 模拟生命周期管理 (CREATED → PREPARING → READY → RUNNING → COMPLETED)
- `SimulationRunner` — 子进程运行、动作日志记录、暂停/停止
- `WorldEvolutionEngine` — LLM 进化推演（规划→多轮推演→整合）
- `Evolution` / `EvolutionRound` — 推演结果数据模型

### 3.4 报告生成 (Step 4)

**API**: `/api/report/*`

`ReportAgent` 使用 **ReACT (Reasoning + Acting)** 模式生成推演报告：

1. 先规划目录结构
2. 分段生成，每段多轮思考+反思
3. 可调用 Zep 检索工具：`InsightForge`（深度洞察）、`PanoramaSearch`（广度搜索）、`QuickSearch`
4. 支持与用户对话（Chat），在对话中自主调用检索工具
5. 生成详细的 `agent_log.jsonl` 记录每一步动作

---

## 4. 技术架构详解

### 4.1 前端 (Vue 3 + Vite)

| 层 | 技术 | 说明 |
|---|---|---|
| 框架 | Vue 3 (Composition API) | `<script setup>` 语法 |
| 构建 | Vite 7 | 开发服务器 + 生产构建 |
| 路由 | Vue Router 4 | `createWebHistory` 模式 |
| 国际化 | Vue I18n 11 | 支持 zh/en/es/fr/pt/ru/de 7种语言 |
| 可视化 | D3.js 7 | 知识图谱力导向图 (GraphPanel) |
| HTTP | Axios | 30分钟超时 + 指数退避重试 + 语言头注入 |
| 样式 | 原生 CSS (CSS Variables) | "Calm Tech Minimalism" 暗色主题 |

**路由表**:
| 路径 | 组件 | 说明 |
|---|---|---|
| `/` | `Home.vue` | 首页/项目列表 |
| `/world-builder` | `WorldBuilderView.vue` | 世界观构建 |
| `/simulation/new` | `SimulationSetup.vue` (lazy) | 推演设置 |
| `/simulation/:id` | `SimulationEvolution.vue` (lazy) | 推演进化展示 |
| `/rag` | `RagView.vue` (lazy) | RAG 向量知识库管理 |

### 4.2 后端 (Flask + Python)

**应用工厂模式**: `create_app()` 在 `app/__init__.py` 中，注册 6 个 Blueprint。

| Blueprint | URL 前缀 | 主要职责 |
|---|---|---|
| `world_build_bp` | `/api/world` | 世界观 CRUD、AI提取、文件上传 |
| `graph_bp` | `/api/graph` | 本体生成、Zep/Local图谱构建、项目上下文管理 |
| `project_bp` | `/api/project` | 项目 CRUD |
| `simulation_bp` | `/api/simulation` | 实体读取、Profile生成、模拟生命周期、Interview |
| `evolution_bp` | `/api/evolution` | LLM世界观进化推演 |
| `report_bp` | `/api/report` | 报告生成、状态查询、对话 |

**核心外部依赖**:
| 依赖 | 版本 | 用途 |
|---|---|---|
| flask | >=3.0.0 | Web 框架 |
| openai | >=1.0.0 | LLM 客户端 (兼容任意 OpenAI SDK 格式 API) |
| zep-cloud | 3.13.0 | 长期记忆图谱 (GraphRAG) |
| camel-oasis | 0.2.5 | OASIS 社交媒体模拟框架 |
| camel-ai | 0.2.78 | CAMEL 多智能体框架 |
| PyMuPDF | >=1.24.0 | PDF 文本提取 |
| pydantic | >=2.0.0 | 数据验证 |

**配置环境变量** (.env):
```
LLM_API_KEY        # LLM API 密钥（必须）
LLM_BASE_URL       # LLM API 地址（默认 OpenAI）
LLM_MODEL_NAME     # 模型名称（默认 gpt-4o-mini）
ZEP_API_KEY        # Zep Cloud API Key（可选，无则用本地图谱）
LLM_BOOST_API_KEY  # 加速 LLM 配置（可选）
```

### 4.3 数据持久化

所有数据以 **JSON 文件** 形式存储于 `backend/uploads/`：

```
uploads/
├── worlds/{world_id}/world.json          # 世界观完整数据
├── projects/{proj_id}/
│   ├── project.json                      # 项目元数据
│   ├── extracted_text.txt                # 提取的纯文本
│   └── files/                            # 上传的原始文件
├── evolutions/{evol_id}.json             # 进化推演结果
├── graphs/{local_xxx}.json               # 本地图谱数据
├── simulations/                          # OASIS 模拟输出
└── reports/{report_id}/                  # 报告 + agent_log.jsonl
```

### 4.4 异步任务管理

长时间运行的任务（如图谱构建、报告生成）通过 `TaskManager` 管理：

- 创建任务 → 返回 task_id
- 后台线程执行 → 实时更新进度
- 前端轮询 `GET /api/xxx/status?task_id=xxx` 获取进度

---

## 5. 设计哲学

**"Calm Tech Minimalism" (克制冷静的科技感)**

- 暗色主题 (background: `rgba(9, 9, 11, 0.85)`)
- 大量留白 + 清晰边界 + 严格网格系统
- 中性灰白 + 少量蓝色强调
- 平滑哑光材质，避免渐变和复杂纹理
- 平滑缓慢的过渡动画

应用到所有前端组件：导航栏、卡片、表单、图谱可视化等。

---

## 6. 开发与部署

### 本地开发
```bash
cp .env.example .env          # 配置环境变量
npm run setup:all             # 安装所有依赖
npm run dev                   # 同时启动前后端
```

- 前端: `http://localhost:3000`
- 后端: `http://localhost:5001`

### Docker 部署
```bash
docker compose up -d          # 映射 3000:3000, 5001:5001
```

### CI/CD
GitHub Actions 自动构建 Docker 镜像并推送到 `ghcr.io/666ghj/mirofish:latest`

---

## 7. 关键文件速查

| 文件 | 用途 |
|---|---|
| `backend/run.py` | 后端入口 |
| `backend/app/__init__.py` | Flask 应用工厂 + 蓝图注册 |
| `backend/app/config.py` | 全局配置（环境变量加载） |
| `backend/app/services/world_evolution_engine.py` | LLM 进化推演核心 |
| `backend/app/services/simulation_manager.py` | OASIS 模拟管理 |
| `backend/app/services/simulation_runner.py` | OASIS 模拟运行器（子进程） |
| `backend/app/services/report_agent.py` | ReACT 报告生成 Agent |
| `backend/app/services/graph_builder.py` | Zep 图谱构建 |
| `backend/app/services/enhanced_world_extractor.py` | AI 世界观提取 |
| `frontend/src/views/WorldBuilderView.vue` | 世界观构建 UI |
| `frontend/src/views/SimulationSetup.vue` | 推演设置 UI |
| `frontend/src/views/SimulationEvolution.vue` | 推演结果展示 UI |
| `frontend/src/components/GraphPanel.vue` | D3.js 知识图谱可视化 |
| `backend/app/services/rag_service.py` | ChromaDB RAG 向量知识库服务 |
| `backend/app/api/rag.py` | RAG REST API |
| `frontend/src/views/RagView.vue` | RAG 知识库管理 UI |
| `frontend/src/api/rag.js` | RAG 前端 API 调用 |

---

## 8. 两种推演模式对比

| 特性 | OASIS 社交媒体模拟 | LLM 世界观进化推演 |
|---|---|---|
| **入口 API** | `/api/simulation/*` | `/api/evolution/*` |
| **驱动方式** | OASIS 框架 (多Agent交互) | 纯 LLM 驱动 |
| **输出形式** | Agent 动作日志 + 社交网络行为 | 叙事文本 + 实体状态变更 |
| **平台模拟** | Twitter + Reddit 双平台 | 无平台概念 |
| **适用场景** | 舆论推演、信息传播模拟 | 世界观时间线推进、历史演化 |
| **记忆系统** | Zep Cloud 图谱记忆 | LLM 上下文窗口 + 累积状态 |
| **实时交互** | Interview (与Agent对话) | 分支推演 + 回退 |
