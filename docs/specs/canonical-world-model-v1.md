# Canonical World Model v1 升级 Spec

## 1. 问题与目标

根据《WorldFish 深度研究分析报告》的软件代码审阅结论，当前仓库已经具备世界观构建、知识图谱、RAG、推演、报告、TRPG、协作与模块系统，但核心数据仍更像散落在页面、API 与模型中的功能集合。`world-builder` 已经是上游模块，其他模块也依赖它，但缺少一个明确、稳定、可测试、可导出的统一世界观模型。

本次升级目标是把“世界观核心”收敛为主仓库内的本地平台内核：

- 定义 `Canonical World Model v1`，统一表达世界基础信息、设定条目、实体、事件、时间线、地图、规则、引用与校验警告。
- 定义 `World Event Schema v1`，为推演回放、TRPG 日志、协作事件和报告生成提供 append-only 事件结构。
- 提供统一世界上下文服务，让 RAG、推演、报告、TRPG 后续可以复用同一份世界数据。
- 新增只读 API，允许本地前端、调试工具与后续导出流程读取 canonical/context 表示。
- 补齐 domain/service/API 层测试，避免继续只依赖页面和 utils 层验证。

## 2. 非目标与边界

本次不做以下事项：

- 不实现官方云账号、登录、团队空间、邀请或组织管理。
- 不实现官方公网 WebSocket 网关、云端协作房间、云同步或云端版本历史。
- 不实现计费、订阅、模板市场、插件市场、运营后台、审计后台或额度体系。
- 不引入云平台 SDK、官方云服务私有环境变量或闭源部署脚本。
- 不把现有 `world_build.py`、`simulation.py`、`report.py` 一次性大拆；本次先新增稳定内核和测试，后续在测试保护下逐步迁移。
- 不强制迁移或重写用户已有世界观数据文件。

本次能力归属为：

- `WorldFish` 主仓库：本地 canonical schema、纯函数归一化、本地上下文构建、本地只读 API、本地测试。
- 未来 `WorldFish-Shared`：可迁移的 schema、类型定义、事件协议与导出协议。
- `WorldFish-Cloud`：账号、团队、计费、市场、公网实时协作、多租户云端能力，不进入本仓库。

## 3. 方案概述

### 后端领域层

新增 `backend/app/domain/canonical_world.py`：

- `CANONICAL_WORLD_MODEL_ID = "worldfish.canonical_world.v1"`
- `CANONICAL_WORLD_MODEL_VERSION = "1.0.0"`
- `build_canonical_world(world)`：把现有 `WorldSetting` 或兼容 dict 转换为 canonical dict。
- `summarize_canonical_world(canonical)`：生成 AI/RAG/报告可复用的摘要。
- `validate_canonical_world(canonical)`：返回 warnings，不对旧数据做硬失败。

新增 `backend/app/domain/world_events.py`：

- `WORLD_EVENT_SCHEMA_ID = "worldfish.world_event.v1"`
- `WORLD_EVENT_SCHEMA_VERSION = "1.0.0"`
- `build_world_event(...)`：创建标准事件。
- `normalize_world_event(raw)`：兼容和补齐旧事件字段。
- `event_to_context_line(event)`：生成可读回放摘要。

### 服务层

新增 `backend/app/services/world_context.py`：

- `build_world_context(world, purpose="general", include_sections=None)`
- `build_world_context_for_rag(world)`
- `build_world_context_for_simulation(world)`
- `build_world_context_for_report(world)`
- `build_world_context_for_trpg(world)`

输出统一包含：

- `schema_id`
- `schema_version`
- `purpose`
- `canonical`
- `summary`
- `sections`
- `warnings`

该服务不调用 LLM、不调用 embedding、不依赖云服务，确保本地零配置可用。

### API 层

新增 `backend/app/api/world_schema.py`，复用现有 `world_build_bp`，挂载在 `/api/world` 前缀下：

- `GET /api/world/<world_id>/canonical`
- `GET /api/world/<world_id>/context?purpose=general|rag|simulation|report|trpg`

新增 API 只读，不改变现有创建、保存、提取、地图等接口。

### 数据兼容

小幅扩展 `WorldSetting`：

- 增加 `schema_version` 字段。
- 旧数据缺失时默认补为 `"1.0.0"`。
- `to_dict()` 输出 schema version。
- 保留未知字段，不删除旧数据。

## 4. 扩展性与本地可用影响

扩展性收益：

- RAG、推演、报告、TRPG 后续可以复用同一份 canonical/context，减少各自拼装 lore 的重复逻辑。
- `World Event Schema v1` 为推演 branch/replay、TRPG 会话日志、协作回放、报告审计提供统一事件底座。
- 纯函数层未来可迁移到 `WorldFish-Shared`，主仓库与云平台都可以依赖共享协议而不是互相依赖实现。
- 新 API 是只读契约，可作为后续导出、导入、测试与前端调试的基础。

本地可用影响：

- 不新增外部服务依赖。
- 不需要 LLM、Embedding、Zep、OpenAI、DeepSeek 或云账号即可读取 canonical/context。
- 旧数据无需迁移即可读取。
- clone 后基础本地运行路径不变。

## 5. 验收标准

本次完成后必须满足：

1. 存在本 Spec，且符合 `docs/WORLDFISH.md` 的 6 项要求。
2. `backend/app/domain/canonical_world.py` 能把旧世界数据转换为 canonical v1。
3. `backend/app/domain/world_events.py` 能构造和归一化世界事件 v1。
4. `GET /api/world/<world_id>/canonical` 返回 `schema_id = worldfish.canonical_world.v1`。
5. `GET /api/world/<world_id>/context?purpose=simulation` 返回统一上下文，且不依赖 LLM / Embedding 配置。
6. 旧世界数据缺少 `schema_version` 时不会失败，并会默认输出 `1.0.0`。
7. 新增后端测试覆盖 canonical、event、context API。
8. `npm run check:oss-boundary` 通过。
9. 不出现云平台实现路径或云平台专属实现标识。

## 6. 测试、迁移与风险

### 测试计划

新增测试文件：

- `backend/tests/test_canonical_world.py`
- `backend/tests/test_world_events.py`
- `backend/tests/test_world_context_api.py`

测试内容：

- 旧世界 dict 缺少 `schema_version` 时可正常加载。
- canonical 输出包含世界基础信息、实体、事件、设定、地图与 warnings。
- world event 输出包含 schema、event id、world id、event type、payload、created_at。
- context API 可返回 general/simulation/report/trpg 等用途化上下文。
- 不配置 LLM / Embedding 时仍可通过。

执行检查：

```bash
cd backend && uv run pytest
npm run check:oss-boundary
```

### 迁移策略

- 本次不做强制文件迁移。
- 读取旧世界时在内存中补齐 `schema_version`。
- 后续保存世界时自然写回 schema version。
- 保留未知字段，避免破坏用户已有数据。

### 风险与缓解

- 旧数据结构不一致：通过 `warnings` 暴露问题，不做硬失败。
- API 行为变化：仅新增只读 API，不改变旧接口。
- 大文件继续膨胀：新增能力放入独立 domain/service/API 文件，避免继续塞进 `world_build.py`。
- 云边界污染：不实现账号、计费、市场、云同步、公网云协作，完成后运行边界检查。
