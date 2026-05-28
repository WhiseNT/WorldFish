<template>
  <div class="modules-page">
    <header class="modules-hero">
      <div>
        <button class="back-link" @click="$router.back()">返回</button>
        <h1>模块管理</h1>
        <p>热启停当前进程中的内置模块。停用后，对应 API 会返回模块停用状态，前端入口也会从导航清单中移除。</p>
      </div>
      <button class="btn btn-secondary" :disabled="loading" @click="loadModules">
        {{ loading ? '刷新中...' : '刷新模块' }}
      </button>
    </header>

    <div v-if="error" class="alert error">{{ error }}</div>

    <section class="module-grid">
      <article v-for="module in modules" :key="module.id" class="module-card card">
        <div class="module-top">
          <div>
            <span class="module-category">{{ categoryLabel(module.category) }}</span>
            <h2>{{ module.name }}</h2>
          </div>
          <span class="status-pill" :class="module.enabled ? 'enabled' : 'disabled'">
            {{ module.enabled ? '已启用' : '已停用' }}
          </span>
        </div>

        <p class="module-desc">{{ module.description || '暂无说明' }}</p>

        <div class="module-meta">
          <span>版本 {{ module.version }}</span>
          <span>{{ module.loaded ? '已加载' : '未加载' }}</span>
          <span v-if="module.depends?.length">依赖：{{ module.depends.join(', ') }}</span>
          <span v-if="module.enabled_dependents?.length">被依赖：{{ module.enabled_dependents.join(', ') }}</span>
        </div>

        <div v-if="module.routes?.length" class="route-list">
          <span v-for="route in module.routes" :key="route">{{ route }}</span>
        </div>

        <div v-if="module.error" class="alert error small">{{ module.error }}</div>

        <div class="module-actions">
          <button
            class="btn btn-secondary"
            :disabled="workingId === module.id || module.id === 'settings'"
            @click="toggleModule(module)"
          >
            {{ module.enabled ? '停用' : '启用' }}
          </button>
          <button
            v-if="module.enabled && module.enabled_dependents?.length"
            class="btn btn-danger"
            :disabled="workingId === module.id || module.id === 'settings'"
            @click="cascadeDisable(module)"
          >
            级联停用
          </button>
          <button class="btn btn-primary" :disabled="workingId === module.id" @click="reloadModule(module)">
            重载
          </button>
        </div>
      </article>
    </section>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { modulesApi } from '../api/modules'
import { useModuleRegistry } from '../modules/registry'

const { modules, loading, error, refreshAll } = useModuleRegistry()
const workingId = ref('')

function categoryLabel(category) {
  return {
    core: '核心',
    ai: 'AI 能力',
    system: '系统',
    general: '通用',
  }[category] || category || '通用'
}

async function loadModules() {
  await refreshAll()
}

async function toggleModule(module) {
  workingId.value = module.id
  try {
    if (module.enabled) await modulesApi.disableModule(module.id)
    else await modulesApi.enableModule(module.id)
    await refreshAll()
  } catch (e) {
    error.value = e.message || '模块状态更新失败'
  } finally {
    workingId.value = ''
  }
}

async function cascadeDisable(module) {
  if (!window.confirm(`级联停用会同时停用依赖 ${module.name} 的模块：${module.enabled_dependents.join(', ')}。是否继续？`)) return
  workingId.value = module.id
  try {
    await modulesApi.disableModule(module.id, { cascade: true })
    await refreshAll()
  } catch (e) {
    error.value = e.message || '级联停用失败'
  } finally {
    workingId.value = ''
  }
}

async function reloadModule(module) {
  workingId.value = module.id
  try {
    await modulesApi.reloadModule(module.id)
    await refreshAll()
  } catch (e) {
    error.value = e.message || '模块重载失败'
  } finally {
    workingId.value = ''
  }
}

onMounted(loadModules)
</script>

<style scoped>
.modules-page {
  max-width: 1120px;
  margin: 0 auto;
  padding: var(--spacing-2xl) var(--spacing-lg);
}

.modules-hero {
  display: flex;
  justify-content: space-between;
  gap: var(--spacing-xl);
  align-items: flex-start;
  margin-bottom: var(--spacing-xl);
  padding-bottom: var(--spacing-lg);
  border-bottom: 1px solid var(--wf-border);
}

.modules-hero h1 {
  margin: var(--spacing-sm) 0;
  font-size: 2rem;
}

.modules-hero p {
  max-width: 760px;
  color: var(--wf-text-secondary);
  line-height: 1.7;
}

.back-link {
  border: 0;
  background: transparent;
  color: var(--wf-accent);
  cursor: pointer;
  padding: 0;
}

.module-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: var(--spacing-lg);
}

.module-card {
  padding: var(--spacing-lg);
}

.module-top {
  display: flex;
  justify-content: space-between;
  gap: var(--spacing-md);
  align-items: flex-start;
  margin-bottom: var(--spacing-md);
}

.module-category {
  color: var(--wf-accent);
  font-size: 12px;
  font-family: var(--font-mono);
}

.module-card h2 {
  margin: 4px 0 0;
  font-size: 1.15rem;
}

.status-pill {
  flex-shrink: 0;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  border: 1px solid var(--wf-border-light);
}

.status-pill.enabled {
  color: #8ee6a2;
  border-color: rgba(142, 230, 162, 0.4);
  background: rgba(142, 230, 162, 0.08);
}

.status-pill.disabled {
  color: var(--wf-text-muted);
  background: rgba(255, 255, 255, 0.04);
}

.module-desc {
  color: var(--wf-text-secondary);
  min-height: 48px;
  line-height: 1.6;
}

.module-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  color: var(--wf-text-muted);
  font-size: 12px;
  margin: var(--spacing-md) 0;
}

.route-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: var(--spacing-md);
}

.route-list span {
  padding: 3px 8px;
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.05);
  color: var(--wf-text-muted);
  font-size: 12px;
  font-family: var(--font-mono);
}

.module-actions {
  display: flex;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-md);
}

.btn-danger {
  color: #ffb4b4;
  border-color: rgba(255, 82, 82, 0.35);
  background: rgba(255, 82, 82, 0.08);
}

.btn-danger:hover:not(:disabled) {
  background: rgba(255, 82, 82, 0.16);
}

.alert {
  padding: 12px 14px;
  border-radius: var(--radius-md);
  margin-bottom: var(--spacing-md);
}

.alert.error {
  color: #ffb4b4;
  background: rgba(255, 82, 82, 0.10);
  border: 1px solid rgba(255, 82, 82, 0.25);
}

.alert.small {
  font-size: 12px;
  padding: 8px 10px;
}
</style>
