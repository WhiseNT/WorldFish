# WorldFish｜创世鱼缸

> 用于创作者的世界观构建、管理与推演工具（开发者导向的仓库说明）。

本仓库保留了项目背景与核心目标，但侧重于面向开发者的使用、运行与部署说明 — 如果需要更详细的产品功能介绍，请参考项目文档或演示资料。

---

## 主要说明（简洁）

- 目标：将文本资料与创意转为结构化的世界观数据，支持 AI 协助的补全与推演。
- 技术栈：后端（Flask/Python）、前端（Vue 3 + Vite）、RAG/向量检索与 LLM 集成；可通过 Docker 部署。

---

## 开发者指南（本地运行）

先决条件：`Python 3.10+`、`node`/`npm`、可选 `docker`/`docker-compose`。

1) 后端（本地）

```bash
# 进入后端目录
cd backend
# 创建并激活虚拟环境（Windows PowerShell 示例）
python -m venv .venv
.\.venv\Scripts\Activate.ps1
# 安装依赖
pip install -r requirements.txt
# 启动后端
python run.py
```

后端默认监听 `0.0.0.0:5001`（可通过环境变量 `FLASK_HOST` / `FLASK_PORT` 调整）。注意：运行时至少需配置一组 LLM API Key（详见下文）。

2) 前端（本地）

```bash
cd frontend
npm install
npm run dev
# 默认 Vite 开发服务器地址： http://localhost:5173
```

（在使用 `docker-compose` 部署时，仓库的 compose 文件会将前端暴露在 `3000` 端口。）

3) 必要环境变量（示例 `.env`）

```
LLM_API_KEY=your-llm-key
FLASK_HOST=0.0.0.0
FLASK_PORT=5001
SECRET_KEY=change-me
EMBEDDING_API_KEY=
ZEP_API_KEY=
```

后端在启动时会验证是否存在至少一组 LLM Key（`LLM_API_KEY` / `SUBAGENT_LLM_API_KEY` / `PARSER_LLM_API_KEY`）。

---

## 部署（Docker / 生产）

推荐使用 `docker-compose` 做快速部署：

```bash
# 构建并启动（后台）
docker-compose up -d --build
# 查看容器日志
docker-compose logs -f mirofish
# 停止并删除容器
docker-compose down
```

默认端口映射（见 `docker-compose.yml`）：
- 前端：宿主机 `3000` -> 容器 `3000`
- 后端：宿主机 `5001` -> 容器 `5001`

手动部署建议：使用生产级 WSGI 服务器（如 `gunicorn`/`uwsgi`）运行后端，并通过 `nginx` 做反向代理与静态文件服务；前端使用 `npm run build` 构建并由静态服务器或 CDN 托管。

---

## 简化的功能概述（仓库层面）

- 世界观结构化管理（实体、地点、势力、时间线等）。
- 基于 LLM 的文本提取与 Agent 协作（用于补全与推演）。
- RAG 支持，用于引用用户提供的世界观资料。
- 简要地图系统用于空间关系管理。

（此处故意保留为简短说明，仓库 README 更侧重于开发、运行与部署说明。）

---

## 代码位置概览

- 后端：`backend/`（Flask 应用，主要代码在 `backend/app/`）
- 前端：`frontend/`（Vue 3 + Vite）
- 脚本与示例：`scripts/` 与 `uploads/`（数据与演示文件）

---

## 贡献与联系方式

欢迎通过 Issue 报告问题或提出功能建议。提交代码请基于 `main` 建立 feature 分支并发起 Pull Request，描述变更目的与运行验证步骤。

---

## 许可证

本项目使用仓库中的 `LICENSE`（请查看仓库根目录的 LICENSE 文件）。
