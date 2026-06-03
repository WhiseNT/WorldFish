# WorldFish 仓库边界

本仓库 `WorldFish` 只承载开源本地单机项目。闭源云平台相关实现必须放入独立仓库，不得提交到本仓库。

## 1. 主仓库定位

`WorldFish` 是开源本地项目仓库，目标是提供可离线、可自托管、可局域网联机的本地世界观工作台。

允许包含：

- 本地世界观构建
- 本地世界模板
- DND / COC 基础跑团模板
- 本地地图编辑
- 方格跑团地图与背景图对齐
- 本地 TRPG 跑团基础能力
- 局域网联机
- 本地 RAG / 用户自带 API Key
- 本地文件 / SQLite / JSON 存储
- SillyTavern 世界书导出
- 本地模块系统
- 可导入导出的开放数据协议

## 2. 云平台与共享仓库定位

闭源云平台必须放在另一个仓库，例如：

```text
WorldFish-Cloud
```

共享协议 / Schema / 通用核心包建议放在另一个独立仓库，例如：

```text
WorldFish-Shared
```

云平台仓库负责：

- 云端账号
- 团队空间
- 权限系统
- 计费系统
- 公网实时协作
- 云端 TRPG 房间
- 云端项目同步
- 云端资源存储 / CDN
- 云端 AI 编排
- 云端 RAG / 向量库
- 模板市场
- 素材市场
- 审计日志
- 商业工作流

## 3. 主仓库禁止出现的内容

`WorldFish` 主仓库不得包含以下实现代码：

- `cloud/`
- `apps/cloud-web/`
- `apps/cloud-api/`
- `apps/cloud-worker/`
- `backend/app/cloud/`
- `frontend/src/cloud/`
- 云端账号实现
- 云端权限实现
- 云端计费实现
- 云端市场实现
- 云端 AI 额度实现
- 云端 WebSocket 协作服务实现
- 云端对象存储 / CDN 的具体实现
- 云平台私有密钥、环境变量、部署脚本

## 4. 主仓库允许保留的云相关边界

为了方便本地版未来连接云平台，本仓库可以保留抽象接口，但不能包含闭源实现。

允许：

```text
StorageAdapter 接口
CollabAdapter 接口
AIAdapter 接口
AssetAdapter 接口
```

允许的本地实现：

```text
LocalFileStorage
LanCollab
UserApiKeyAI
LocalAssetStorage
```

不允许的闭源实现：

```text
CloudStorage
CloudRealtime
CloudAIOrchestrator
CloudBilling
CloudMarketplace
```

这些必须在云平台仓库实现。

## 5. 推荐仓库职责

### WorldFish

开源本地项目：

```text
backend/
frontend/
shared/
packages/ 开源核心包
modules/ 开源模块
scripts/ 本地开发与检查脚本
```

### WorldFish-Shared

共享协议与开源通用包：

```text
shared/schemas/
shared/types/
packages/schema/
packages/templates/
packages/maps/
packages/trpg/
packages/exports/
```

它应该承载：

- WorldFish / WorldFish-Cloud 共用的数据协议
- 模板结构
- 地图结构
- TRPG 事件结构
- 导出结构
- 可复用的纯函数与规范化逻辑

### 建议从 WorldFish 迁出的内容

以下内容建议尽快迁移到 `WorldFish-Shared`，以减少主仓库与云平台的耦合，且优先只迁移纯函数/协议/模板数据，不迁移 UI 与路由：

- `frontend/src/utils/trpgMap.js`
- `frontend/src/utils/trpgDice.js`
- `frontend/src/utils/sillyTavernWorldBook.js`
- `frontend/src/utils/collabIdentity.js`
- `frontend/src/utils/entityCardLayoutPreference.js`
- `backend/app/services/world_templates.py` 中的模板定义数据
- `backend/app/models/map.py` 中的纯地图数据规范化逻辑
- `backend/app/models/world.py` 中与 schema / 规范化相关的纯函数

建议留在 `WorldFish` 的内容：

- Flask 路由
- Vue 页面
- 本地数据库与文件存储实现
- LAN 联机实现
- 本地 AI / RAG 调用
- 模块注册与本地启动脚本

### WorldFish-Cloud

闭源云平台：

```text
apps/cloud-web/
apps/cloud-api/
apps/cloud-worker/
cloud/auth/
cloud/billing/
cloud/realtime/
cloud/storage/
cloud/ai/
cloud/marketplace/
cloud/permissions/
infra/cloud/
```

## 6. 依赖方向约束

推荐依赖方向始终是：

```text
WorldFish -> WorldFish-Shared
WorldFish-Cloud -> WorldFish-Shared
```

不推荐且应避免：

```text
WorldFish-Cloud -> WorldFish
```

`WorldFish` 可以包含可发布的开源应用代码，但不应被当作共享库来被云平台直接依赖。

## 7. 提交流程要求

在向 `WorldFish` 主仓库提交前，应运行：

```bash
npm run check:oss-boundary
```

如果检查发现云平台实现路径或云平台专属关键词，应将相关代码移动到云平台仓库。
