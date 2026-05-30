# WorldFish｜创世鱼缸

WorldFish 是一个面向创作者的世界观构建、知识组织与推演工具。当前仓库侧重于**项目管理、知识图谱、RAG 检索、Agent 协作、模拟推演与报告生成**，前端采用 Vue 3，后端采用 Flask。

## 主要能力

- 世界观与项目结构化管理：角色、地点、势力、时间线、关系等
- 知识图谱与关系可视化
- 资料导入与 RAG 检索
- Agent 协作式提取、整理与补全
- 世界演化与模拟运行链路
- 自动化报告生成与总结
- 前后端分离：Vue 3 + Vite 前端，Flask 后端

## 技术栈

- 后端：Python 3.11+、Flask、Flask-CORS
- 前端：Vue 3、Vite、D3、Vue Router、Vue I18n
- 工具：uv、npm、Docker / Docker Compose

## 仓库结构

- `backend/`：Flask 后端，主要代码位于 `backend/app/`
- `frontend/`：Vue 3 前端应用
- `prompts/`：提取、校验、写作相关提示词
- `locales/`：多语言资源
- `uploads/`：上传与模拟数据目录

## 本地快速开始

### 1. 安装依赖

建议在仓库根目录执行：

```bash
npm run setup:all
```

该命令会：

- 安装根目录依赖
- 安装 `frontend/` 依赖
- 同步 `backend/` 的 Python 依赖（通过 `uv sync`）

如果你想分开执行，也可以：

```bash
npm install
cd frontend && npm install
cd backend && uv sync
```

### 2. 配置 API Key

后端启动不再要求项目根目录存在 `.env` 文件，也不会在启动时强制检查 LLM API Key。

首次打开前端后，请进入 **LLM 配置** 页面填写 API Key、Base URL 和模型名称。保存后，后端会把配置写入根目录 `.env`，后续启动会自动读取。

说明：

- 推荐通过 GUI 维护 API Key，不需要手动创建 `.env`
- 如果暂未配置 API Key，应用仍可启动；调用世界构建、推演、RAG 等依赖模型的功能时会提示先配置
- Agent、SubAgent、解析 Agent 可以在 GUI 中分别配置；未单独配置时会按现有回退规则复用可用配置
- Embedding 未单独配置 API Key 时，会复用主 Agent 的 API Key 与 Base URL
- `.env.example` 仅作为高级配置与旧部署方式参考，可选填写 `SECRET_KEY`、`FLASK_HOST`、`FLASK_PORT`、默认模型等配置

### 3. 启动开发环境

推荐在仓库根目录启动：

```bash
npm run dev
```

默认情况下：

- 前端开发服务器：`http://localhost:3000`
- 后端服务：`http://localhost:5001`
- 前端会通过 Vite 代理把 `/api` 转发到后端

如果你想单独启动：

```bash
# 后端
npm run backend

# 前端
npm run frontend
```

也可以直接进入子目录运行：

```bash
cd backend && uv run python run.py
cd frontend && npm run dev
```

## Docker 部署

仓库提供了 `docker-compose.yml`，默认使用镜像方式部署。

```bash
docker compose up -d
```

说明：

- 默认不需要提前准备 `.env`，API Key 可在启动后通过前端 **LLM 配置** 页面填写
- 如需预置端口、密钥或模型配置，可参考 `.env.example` 自行创建 `.env`
- 默认端口：前端 `3000`、后端 `5001`
- `backend/uploads` 会被挂载到容器中，用于保存上传数据与模拟数据

如果你需要查看日志：

```bash
docker compose logs -f worldfish
```

停止服务：

```bash
docker compose down
```

## 常用脚本

根目录 `package.json` 提供了这些脚本：

- `npm run setup`：安装根目录依赖并安装前端依赖
- `npm run setup:backend`：同步后端 Python 依赖
- `npm run setup:all`：一次性完成全部依赖安装
- `npm run dev`：同时启动后端和前端开发环境
- `npm run backend`：仅启动后端
- `npm run frontend`：仅启动前端
- `npm run build`：构建前端生产包

## 说明

- 本仓库当前更偏向开发与迭代状态，README 重点放在实际运行方式和项目结构上
- 如果你要快速了解后端入口，可以从 `backend/run.py` 和 `backend/app/__init__.py` 开始
- 如果你要查看 API 路由，可从 `backend/app/api/` 目录入手

## 许可证

本项目许可证见仓库根目录的 `LICENSE` 文件。
