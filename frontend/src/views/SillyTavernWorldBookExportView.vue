<template>
  <div class="worldbook-export-page">
    <header class="export-hero">
      <div>
        <button type="button" class="back-link" @click="router.push('/')">
          <SvgIcon name="chevron-left" :size="16" :stroke-width="2.2" />
          <span>返回首页</span>
        </button>
        <h1>SillyTavern 世界书导出</h1>
        <p>选择一个 WorldFish 世界观，将实体、事件和设定转换为 SillyTavern World Info / 世界书 JSON。</p>
      </div>
      <button class="btn btn-secondary" :disabled="loadingWorlds" @click="loadWorlds">刷新世界观</button>
    </header>

    <div v-if="error" class="alert error">{{ error }}</div>
    <div v-if="copyFeedback" class="alert success">{{ copyFeedback }}</div>

    <section class="export-layout">
      <aside class="export-sidebar card">
        <div class="panel-head">
          <h2>选择世界观</h2>
          <span>{{ worlds.length }} 个</span>
        </div>

        <div v-if="loadingWorlds" class="state-box">正在加载世界观...</div>
        <div v-else-if="worlds.length === 0" class="state-box">暂无世界观，请先创建或导入世界观。</div>
        <template v-else>
          <button
            v-for="world in worlds"
            :key="world.id"
            type="button"
            class="world-option"
            :class="{ active: selectedWorldId === world.id }"
            @click="selectedWorldId = world.id"
          >
            <strong>{{ world.name || '未命名世界观' }}</strong>
            <small>{{ world.entities_count || 0 }} 实体 · {{ world.events_count || 0 }} 事件</small>
          </button>
        </template>
      </aside>

      <main class="export-main card">
        <div class="panel-head export-title-row">
          <div>
            <h2>{{ currentWorld?.name || '未选择世界观' }}</h2>
            <p>{{ currentWorld?.description || '选择世界观后会生成 SillyTavern 世界书预览。' }}</p>
          </div>
          <div class="entry-count-card">
            <span>条目数</span>
            <strong>{{ entryCount }}</strong>
          </div>
        </div>

        <div class="option-grid">
          <label v-for="option in optionItems" :key="option.key" class="option-item">
            <input type="checkbox" v-model="exportOptions[option.key]" />
            <span>
              <strong>{{ option.label }}</strong>
              <small>{{ option.description }}</small>
            </span>
          </label>
        </div>

        <div class="range-row">
          <label>
            默认触发深度
            <input v-model.number="exportOptions.defaultDepth" type="number" min="0" max="20" step="1" />
          </label>
          <label>
            概览常驻
            <select v-model="exportOptions.constantOverview">
              <option :value="true">是</option>
              <option :value="false">否</option>
            </select>
          </label>
        </div>

        <div class="actions-row">
          <button class="btn btn-primary" :disabled="!canExport" @click="downloadWorldBook">导出世界书 JSON</button>
          <button class="btn btn-secondary" :disabled="!canExport" @click="copyJson">复制 JSON</button>
          <router-link
            v-if="selectedWorldId"
            class="btn btn-secondary"
            :to="{ name: 'WorldBuilder', query: { worldId: selectedWorldId } }"
          >编辑世界观</router-link>
        </div>

        <section class="preview-section">
          <div class="preview-head">
            <h3>JSON 预览</h3>
            <span>{{ fileName }}</span>
          </div>
          <pre v-if="canExport" class="json-preview">{{ previewJson }}</pre>
          <div v-else class="state-box preview-empty">请选择一个世界观以生成预览。</div>
        </section>
      </main>
    </section>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { worldApi } from '../api/world'
import SvgIcon from '../components/ui/SvgIcon.vue'
import {
  DEFAULT_EXPORT_OPTIONS,
  buildSillyTavernWorldBook,
  countWorldBookEntries,
  createWorldBookFileName,
} from '../utils/sillyTavernWorldBook.js'

const route = useRoute()
const router = useRouter()

const worlds = ref([])
const currentWorld = ref(null)
const selectedWorldId = ref(String(route.query.worldId || '').trim())
const loadingWorlds = ref(false)
const loadingWorld = ref(false)
const error = ref('')
const copyFeedback = ref('')
let copyFeedbackTimer = null

const exportOptions = reactive({ ...DEFAULT_EXPORT_OPTIONS })

const optionItems = [
  { key: 'includeOverview', label: '世界观概览', description: '导出名称、时代、锚定时间、简介和文风。' },
  { key: 'includeEntities', label: '实体', description: '导出人物、组织、地点、物品、能力等实体。' },
  { key: 'includeEvents', label: '事件', description: '导出关键事件、时间和关联实体。' },
  { key: 'includeSettings', label: '设定项', description: '导出设定管理中的结构化设定。' },
  { key: 'includeStages', label: '成长阶段', description: '在实体和设定中包含阶段/演变内容。' },
  { key: 'includeRelationships', label: '关系网络', description: '在实体和设定中包含关系描述。' },
  { key: 'includeAliases', label: '别名触发词', description: '将实体和设定别名加入 SillyTavern key。' },
]

const worldBook = computed(() => currentWorld.value ? buildSillyTavernWorldBook(currentWorld.value, exportOptions) : null)
const entryCount = computed(() => worldBook.value ? countWorldBookEntries(worldBook.value) : 0)
const canExport = computed(() => Boolean(currentWorld.value && entryCount.value > 0 && !loadingWorld.value))
const fileName = computed(() => currentWorld.value ? createWorldBookFileName(currentWorld.value) : 'worldfish-worldbook.json')
const previewJson = computed(() => worldBook.value ? JSON.stringify(worldBook.value, null, 2) : '')

async function loadWorlds() {
  loadingWorlds.value = true
  error.value = ''
  try {
    const res = await worldApi.listWorlds()
    worlds.value = res.worlds || []
    if (!selectedWorldId.value && worlds.value.length) {
      selectedWorldId.value = worlds.value[0].id
    }
  } catch (e) {
    error.value = '加载世界观列表失败：' + (e.message || '网络错误')
  } finally {
    loadingWorlds.value = false
  }
}

async function loadWorld(worldId) {
  const id = String(worldId || '').trim()
  currentWorld.value = null
  if (!id) return
  loadingWorld.value = true
  error.value = ''
  try {
    const res = await worldApi.getWorld(id)
    currentWorld.value = res.world
  } catch (e) {
    error.value = '加载世界观详情失败：' + (e.message || '网络错误')
  } finally {
    loadingWorld.value = false
  }
}

function downloadWorldBook() {
  if (!canExport.value) return
  const blob = new Blob([previewJson.value], { type: 'application/json;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = fileName.value
  link.click()
  URL.revokeObjectURL(url)
}

async function copyJson() {
  if (!canExport.value) return
  try {
    if (!navigator.clipboard) throw new Error('clipboard unavailable')
    await navigator.clipboard.writeText(previewJson.value)
    showCopyFeedback('JSON 已复制到剪贴板')
  } catch (e) {
    showCopyFeedback('复制失败，请手动复制预览内容')
  }
}

function showCopyFeedback(message) {
  copyFeedback.value = message
  if (copyFeedbackTimer) clearTimeout(copyFeedbackTimer)
  copyFeedbackTimer = setTimeout(() => {
    copyFeedback.value = ''
  }, 2500)
}

watch(selectedWorldId, (worldId) => {
  if (worldId) {
    router.replace({ name: 'SillyTavernWorldBookExport', query: { worldId } })
  }
  loadWorld(worldId)
}, { immediate: true })

onMounted(async () => {
  await loadWorlds()
})

onBeforeUnmount(() => {
  if (copyFeedbackTimer) clearTimeout(copyFeedbackTimer)
})
</script>

<style scoped>
.worldbook-export-page {
  max-width: 1280px;
  margin: 0 auto;
  padding: var(--spacing-2xl) var(--spacing-lg);
}

.export-hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--spacing-xl);
  margin-bottom: var(--spacing-xl);
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: 0;
  background: transparent;
  color: var(--wf-text-muted);
  cursor: pointer;
  padding: 0;
  margin-bottom: var(--spacing-sm);
  font-size: 14px;
  font-weight: 500;
}

.back-link:hover {
  color: var(--wf-accent-hover);
}

.export-hero h1 {
  margin-bottom: var(--spacing-sm);
  font-size: 2rem;
}

.export-hero p,
.panel-head p {
  color: var(--wf-text-secondary);
  line-height: 1.7;
}

.export-layout {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: var(--spacing-lg);
  align-items: start;
}

.card {
  padding: var(--spacing-lg);
}

.panel-head,
.export-title-row,
.preview-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-md);
}

.panel-head h2,
.preview-head h3 {
  margin: 0;
}

.panel-head span,
.preview-head span {
  color: var(--wf-text-muted);
}

.world-option {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding: 12px;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--wf-text-primary);
  text-align: left;
  cursor: pointer;
  margin-bottom: 8px;
}

.world-option:hover,
.world-option.active {
  background: rgba(255, 255, 255, 0.06);
  border-color: var(--wf-border-light);
}

.world-option small,
.state-box,
.option-item small {
  color: var(--wf-text-muted);
}

.state-box {
  padding: var(--spacing-lg);
  border: 1px dashed var(--wf-border);
  border-radius: var(--radius-md);
  text-align: center;
  background: rgba(255, 255, 255, 0.025);
}

.entry-count-card {
  min-width: 86px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 12px;
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.035);
  text-align: right;
}

.entry-count-card span {
  color: var(--wf-text-muted);
  font-size: 12px;
}

.entry-count-card strong {
  color: var(--wf-accent);
  font-size: 1.4rem;
}

.option-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-md);
}

.option-item {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 12px;
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.035);
}

.option-item input {
  margin-top: 3px;
}

.option-item span {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.range-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
}

.range-row label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: var(--wf-text-secondary);
  min-width: 180px;
}

.range-row input,
.range-row select {
  padding: 9px 10px;
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.04);
  color: var(--wf-text-primary);
}

.actions-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-lg);
}

.preview-section {
  border-top: 1px solid var(--wf-border);
  padding-top: var(--spacing-md);
}

.json-preview {
  max-height: 520px;
  overflow: auto;
  padding: var(--spacing-md);
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-md);
  background: rgba(0, 0, 0, 0.26);
  color: var(--wf-text-secondary);
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 1.55;
  white-space: pre-wrap;
}

.preview-empty {
  min-height: 220px;
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

.alert.success {
  color: #b8f5d0;
  background: rgba(16, 185, 129, 0.10);
  border: 1px solid rgba(16, 185, 129, 0.25);
}

@media (max-width: 960px) {
  .export-layout {
    grid-template-columns: 1fr;
  }

  .export-hero,
  .export-title-row,
  .preview-head {
    flex-direction: column;
  }
}
</style>
