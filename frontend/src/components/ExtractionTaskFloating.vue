<template>
  <div v-if="shouldShow" class="extract-floating-root">
    <button v-if="minimized" class="extract-mini-btn" :class="statusClass" @click="minimized = false" title="世界观解析任务">
      <span class="extract-mini-icon"><SvgIcon name="grid" :size="20" /></span>
      <span class="extract-mini-pulse" v-if="isActiveTask"></span>
    </button>

    <section v-else class="extract-window">
      <header class="extract-header">
        <div>
          <div class="extract-kicker">世界观解析任务</div>
          <h3>{{ taskTitle }}</h3>
        </div>
        <button class="extract-icon-btn" @click="minimized = true" title="最小化"><SvgIcon name="minus" :size="15" /></button>
      </header>

      <div class="extract-body">
        <div class="extract-status-row">
          <span class="extract-status" :class="statusClass">{{ statusLabel }}</span>
          <span class="extract-percent">{{ progress }}%</span>
        </div>
        <div class="extract-progress-bar">
          <div class="extract-progress-fill" :style="{ width: progress + '%' }"></div>
        </div>
        <p class="extract-message">{{ currentTask.message || '等待任务状态...' }}</p>
        <p v-if="completionText" class="extract-complete-note">{{ completionText }}</p>
        <p v-if="estimateText" class="extract-estimate-note">{{ estimateText }}<span v-if="estimateSourceText">（{{ estimateSourceText }}）</span></p>
        <p v-if="activityText" class="extract-live-note"><span class="extract-live-dot"></span>{{ activityText }}</p>

        <div v-if="isCompletedTask" class="extract-meta-grid">
          <div>
            <span>实体</span>
            <strong>{{ finalSummary.entities }}</strong>
          </div>
          <div>
            <span>事件</span>
            <strong>{{ finalSummary.events }}</strong>
          </div>
          <div>
            <span>设定</span>
            <strong>{{ finalSummary.settings }}</strong>
          </div>
          <div>
            <span>完成时间</span>
            <strong>{{ finishedText }}</strong>
          </div>
        </div>
        <div v-else class="extract-meta-grid">
          <div>
            <span>块进度</span>
            <strong>{{ processedChunks }}/{{ detail.total_chunks || 0 }}</strong>
          </div>
          <div>
            <span>已处理</span>
            <strong>{{ detail.processed_chars_label || `${detail.processed_chars || 0}字` }}</strong>
          </div>
          <div>
            <span>当前阅读</span>
            <strong>{{ deepState.current_chunk_title || '准备中' }}</strong>
          </div>
          <div>
            <span>最近心跳</span>
            <strong>{{ heartbeatText || '等待中' }}</strong>
          </div>
          <div>
            <span>实体快照</span>
            <strong>{{ deepState.confirmed_entity_count || deepState.snapshot_stats?.entity_count || 0 }}</strong>
          </div>
          <div>
            <span>当前块耗时</span>
            <strong>{{ runtimeText || '0秒' }}</strong>
          </div>
        </div>

        <div v-if="discoveries.length" class="extract-discoveries">
          <div class="extract-section-title">实时发现</div>
          <ul>
            <li v-for="item in discoveries" :key="item">{{ item }}</li>
          </ul>
        </div>

        <div v-if="summaryText" class="extract-summary">
          <div class="extract-section-title">模型摘要</div>
          <p>{{ summaryText }}</p>
        </div>

        <div class="extract-actions">
          <button v-if="canPause" class="extract-action-btn" @click="pauseTask" :disabled="busy">暂停</button>
          <button v-if="canResume" class="extract-action-btn primary" @click="resumeTask" :disabled="busy">继续</button>
          <button v-if="canCancel" class="extract-action-btn danger" @click="cancelTask" :disabled="busy">强制中止</button>
          <button class="extract-action-btn" @click="openScanPanel">打开扫描面板</button>
          <button class="extract-action-btn" @click="goWorldBuilder">查看世界观</button>
          <button v-if="canDelete" class="extract-action-btn danger" @click="deleteTask" :disabled="busy">删除扫描</button>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { worldApi } from '../api/world'
import SvgIcon from './ui/SvgIcon.vue'

const LAST_TASK_KEY = 'worldfish:lastExtractTaskId'
const TASK_DELETED_EVENT = 'worldfish:extract-task-deleted'
const TASK_SYNC_EVENT = 'worldfish:extract-task-sync'
const minimized = ref(true)
const currentTask = ref(null)
const busy = ref(false)
const router = useRouter()
let timer = null
let uiTickTimer = null
const uiTick = ref(0)

const status = computed(() => currentTask.value?.status || currentTask.value?.stage || '')
const detail = computed(() => currentTask.value?.detail || {})
const deepState = computed(() => detail.value.deep_state || currentTask.value?.deep_state || {})
const progress = computed(() => Math.max(0, Math.min(100, Math.round(Number(currentTask.value?.progress || 0)))))
const processedChunks = computed(() => {
  const completed = Number(detail.value.completed_chunks || 0)
  const failed = Number(detail.value.failed_chunks || 0)
  return Number(detail.value.processed_chunks ?? (completed + failed)) || 0
})
const discoveries = computed(() => Array.isArray(deepState.value.discoveries) ? deepState.value.discoveries : [])
const summaryText = computed(() => deepState.value.rolling_summary_preview || '')
const activeStatuses = ['running', 'extracting', 'preparing', 'chunking', 'indexing', 'starting', 'pause_requested', 'cancel_requested']
const isActiveTask = computed(() => activeStatuses.includes(status.value) || Boolean(currentTask.value?.running))
const canPause = computed(() => ['running', 'extracting', 'preparing', 'chunking', 'indexing', 'starting'].includes(status.value))
const canResume = computed(() => ['paused', 'stale', 'cancelled'].includes(status.value))
const canCancel = computed(() => ['running', 'extracting', 'preparing', 'chunking', 'indexing', 'starting', 'pause_requested', 'paused', 'stale'].includes(status.value))
const canDelete = computed(() => ['paused', 'stale', 'cancelled', 'failed', 'error', 'completed', 'done'].includes(status.value) || (currentTask.value?.done && ['pause_requested', 'cancel_requested'].includes(status.value)))
const shouldShow = computed(() => Boolean(currentTask.value) && (isActiveTask.value || canResume.value || canDelete.value))
const taskTitle = computed(() => currentTask.value?.extraction_mode === 'deep' ? '深度扫描' : '快速扫描')
const statusLabel = computed(() => ({
  running: '运行中',
  starting: '启动中',
  preparing: '准备中',
  chunking: '切分中',
  indexing: '索引中',
  extracting: '解析中',
  pause_requested: '暂停中',
  paused: '已暂停',
  cancel_requested: '强制中止中',
  cancelled: '已强制中止，可继续',
  stale: '上次意外暂停，可继续',
  failed: '失败',
  error: '失败',
  done: '完成',
  completed: '完成',
}[status.value] || '准备中'))
const statusClass = computed(() => `is-${status.value || 'idle'}`)
const isCompletedTask = computed(() => ['completed', 'done'].includes(status.value))
const estimatedChars = computed(() => Number(currentTask.value?.estimated_text_chars || detail.value.estimated_text_chars || detail.value.total_chars || 0))
const estimateText = computed(() => {
  if (!estimatedChars.value) return ''
  return `预估总文本：${currentTask.value?.estimated_text_chars_label || detail.value.estimated_text_chars_label || formatCharCount(estimatedChars.value)}`
})
const estimateSourceText = computed(() => {
  const items = Array.isArray(currentTask.value?.text_estimate_breakdown) ? currentTask.value.text_estimate_breakdown : []
  return items.slice(0, 3).map(item => `${item.name || '文本'} ${item.chars_label || formatCharCount(item.chars || 0)}`).join('；')
})
const finalSummary = computed(() => {
  const result = currentTask.value?.extracted_data || currentTask.value?.result || {}
  const settings = result.settings || {}
  const fallback = {
    entities: Array.isArray(result.entities) ? result.entities.length : 0,
    events: Array.isArray(result.events) ? result.events.length : 0,
    settings: Array.isArray(settings.items) ? settings.items.length : 0,
  }
  const summary = currentTask.value?.result_summary || fallback
  return {
    entities: Number(summary.entities || 0),
    events: Number(summary.events || 0),
    settings: Number(summary.settings || 0),
  }
})
const completionText = computed(() => {
  if (!isCompletedTask.value) return ''
  return `扫描已完成：提取到 ${finalSummary.value.entities} 个实体、${finalSummary.value.events} 个事件${finalSummary.value.settings ? `、${finalSummary.value.settings} 条设定` : ''}。`
})
const finishedText = computed(() => {
  const timestamp = currentTask.value?.finished_at || currentTask.value?.updated_at || currentTask.value?.updatedAt
  if (!timestamp) return '刚刚'
  const seconds = secondsSince(timestamp)
  if (seconds <= 3) return '刚刚'
  if (seconds < 60) return `${seconds}秒前`
  return formatDuration(seconds) + '前'
})
const runtimeText = computed(() => {
  uiTick.value
  const elapsed = Number(deepState.value.current_chunk_elapsed_seconds || 0)
  const startedAt = deepState.value.current_chunk_started_at
  const seconds = elapsed || secondsSince(startedAt)
  return seconds ? formatDuration(seconds) : ''
})
const heartbeatText = computed(() => {
  uiTick.value
  const heartbeatAt = deepState.value.current_chunk_heartbeat_at || currentTask.value?.updated_at || currentTask.value?.updatedAt
  if (!heartbeatAt) return ''
  const seconds = secondsSince(heartbeatAt)
  return seconds <= 1 ? '刚刚' : `${seconds}秒前`
})
const activityText = computed(() => {
  if (!isActiveTask.value) return ''
  const parts = []
  if (runtimeText.value) parts.push(`当前块已运行 ${runtimeText.value}`)
  if (heartbeatText.value) parts.push(`最近心跳 ${heartbeatText.value}`)
  return parts.length ? `扫描仍在运行：${parts.join('，')}` : '扫描仍在运行，正在等待最新进度...'
})

function formatDuration(seconds) {
  const safeSeconds = Math.max(0, Math.round(Number(seconds || 0)))
  if (safeSeconds >= 3600) return `${Math.floor(safeSeconds / 3600)}时${Math.floor((safeSeconds % 3600) / 60)}分`
  if (safeSeconds >= 60) return `${Math.floor(safeSeconds / 60)}分${safeSeconds % 60}秒`
  return `${safeSeconds}秒`
}

function formatCharCount(chars) {
  const safeChars = Math.max(0, Math.round(Number(chars || 0)))
  if (safeChars >= 10000) return `${(safeChars / 10000).toFixed(1)}万字`
  return `${safeChars}字`
}

function secondsSince(timestamp) {
  if (!timestamp) return 0
  const time = new Date(timestamp).getTime()
  if (!Number.isFinite(time)) return 0
  return Math.max(0, Math.round((Date.now() - time) / 1000))
}

function startUiTicker() {
  if (uiTickTimer) return
  uiTickTimer = window.setInterval(() => { uiTick.value += 1 }, 1000)
}

function stopUiTicker() {
  if (!uiTickTimer) return
  clearInterval(uiTickTimer)
  uiTickTimer = null
}

function schedule(ms = 1500) {
  clearTimeout(timer)
  if (isActiveTask.value) {
    startUiTicker()
    timer = setTimeout(refreshCurrentTask, ms)
  } else {
    stopUiTicker()
  }
}

function clearStoredTaskId(taskId) {
  if (!taskId || localStorage.getItem(LAST_TASK_KEY) === taskId) {
    localStorage.removeItem(LAST_TASK_KEY)
  }
}

function emitTaskDeleted(taskId) {
  window.dispatchEvent(new CustomEvent(TASK_DELETED_EVENT, { detail: { taskId } }))
}

function handleExternalTaskDeleted(event) {
  const taskId = event.detail?.taskId
  if (!taskId || currentTask.value?.task_id !== taskId) return
  clearStoredTaskId(taskId)
  currentTask.value = null
  clearTimeout(timer)
  stopUiTicker()
}

function handleTaskSync(event) {
  const taskId = event.detail?.taskId
  if (!taskId) return
  localStorage.setItem(LAST_TASK_KEY, taskId)
  currentTask.value = normalizeTask({
    ...currentTask.value,
    task_id: taskId,
    world_id: event.detail?.worldId || currentTask.value?.world_id,
    extraction_mode: event.detail?.extractionMode || currentTask.value?.extraction_mode,
    status: event.detail?.status || 'running',
    stage: event.detail?.stage || 'starting',
    progress: event.detail?.progress || currentTask.value?.progress || 0,
    message: event.detail?.message || '提取任务已启动',
    detail: event.detail?.detail || currentTask.value?.detail || {},
    rag_progress: event.detail?.ragProgress || event.detail?.rag_progress || currentTask.value?.rag_progress || null,
    updated_at: event.detail?.updatedAt || event.detail?.updated_at || currentTask.value?.updated_at,
    started_at: event.detail?.startedAt || event.detail?.started_at || currentTask.value?.started_at,
    finished_at: event.detail?.finishedAt || event.detail?.finished_at || currentTask.value?.finished_at,
    running: event.detail?.running ?? currentTask.value?.running,
    done: event.detail?.done ?? currentTask.value?.done,
    result_summary: event.detail?.resultSummary || event.detail?.result_summary || currentTask.value?.result_summary,
    extracted_data: event.detail?.extractedData || event.detail?.extracted_data || currentTask.value?.extracted_data,
    estimated_text_chars: event.detail?.estimatedTextChars ?? event.detail?.estimated_text_chars ?? currentTask.value?.estimated_text_chars,
    estimated_text_chars_label: event.detail?.estimatedTextCharsLabel || event.detail?.estimated_text_chars_label || currentTask.value?.estimated_text_chars_label,
    text_estimate_breakdown: event.detail?.textEstimateBreakdown || event.detail?.text_estimate_breakdown || currentTask.value?.text_estimate_breakdown || [],
  })
  minimized.value = false
  clearTimeout(timer)
  schedule(250)
}

async function loadInitialTask() {
  const lastTaskId = localStorage.getItem(LAST_TASK_KEY)
  if (lastTaskId) {
    try {
      const progress = await worldApi.getExtractProgress(lastTaskId)
      currentTask.value = normalizeTask(progress)
      minimized.value = false
      schedule()
      return
    } catch (e) {
      clearStoredTaskId(lastTaskId)
    }
  }
  try {
    const res = await worldApi.listExtractTasks({ active: 1, limit: 1 })
    const task = (res.tasks || [])[0]
    if (task) {
      currentTask.value = normalizeTask(task)
      localStorage.setItem(LAST_TASK_KEY, task.task_id)
      minimized.value = false
      schedule()
    }
  } catch (e) {
    console.warn('加载解析任务失败:', e)
  }
}

function normalizeTask(task) {
  const rawDetail = task.detail || {}
  const completed = task.completed_chunks ?? rawDetail.completed_chunks
  const failed = task.failed_chunks ?? rawDetail.failed_chunks
  return {
    ...task,
    task_id: task.task_id,
    world_id: task.world_id,
    status: task.status || task.stage,
    estimated_text_chars: task.estimated_text_chars ?? rawDetail.estimated_text_chars ?? rawDetail.total_chars ?? 0,
    estimated_text_chars_label: task.estimated_text_chars_label || rawDetail.estimated_text_chars_label || '',
    text_estimate_breakdown: task.text_estimate_breakdown || rawDetail.text_estimate_breakdown || [],
    detail: {
      ...rawDetail,
      completed_chunks: completed,
      failed_chunks: failed,
      processed_chunks: task.processed_chunks ?? rawDetail.processed_chunks ?? ((Number(completed || 0) + Number(failed || 0)) || 0),
      total_chunks: task.total_chunks ?? rawDetail.total_chunks,
      processed_chars: task.processed_chars ?? rawDetail.processed_chars,
      processed_chars_label: task.processed_chars_label || rawDetail.processed_chars_label,
    },
    progress: task.progress || 0,
  }
}

async function refreshCurrentTask() {
  if (!currentTask.value?.task_id) return
  try {
    const res = await worldApi.getExtractProgress(currentTask.value.task_id)
    currentTask.value = normalizeTask({ ...res, world_id: res.world_id || currentTask.value?.world_id })
    if (['completed', 'done', 'failed', 'error'].includes(status.value)) {
      clearStoredTaskId(currentTask.value.task_id)
    }
  } catch (e) {
    console.warn('刷新解析任务失败:', e)
  } finally {
    schedule()
  }
}

async function pauseTask() {
  await runAction(() => worldApi.pauseExtract(currentTask.value.task_id))
}

async function resumeTask() {
  await runAction(() => worldApi.resumeExtract(currentTask.value.task_id))
}

async function cancelTask() {
  await runAction(() => worldApi.cancelExtract(currentTask.value.task_id))
}

async function deleteTask() {
  if (!currentTask.value?.task_id || busy.value) return
  if (!confirm('确定删除这条扫描记录吗？不会删除已合并到世界观的数据。')) return
  busy.value = true
  const taskId = currentTask.value.task_id
  try {
    await worldApi.deleteExtractTask(taskId)
    clearStoredTaskId(taskId)
    currentTask.value = null
    clearTimeout(timer)
    stopUiTicker()
    emitTaskDeleted(taskId)
  } finally {
    busy.value = false
  }
}

async function runAction(fn) {
  if (!currentTask.value?.task_id || busy.value) return
  busy.value = true
  try {
    await fn()
    await refreshCurrentTask()
  } finally {
    busy.value = false
  }
}

function openScanPanel() {
  const query = {
    ...(currentTask.value?.world_id ? { worldId: currentTask.value.world_id } : {}),
    extractTaskId: currentTask.value?.task_id,
    showExtractPanel: '1',
  }
  router.push({ name: 'WorldBuilder', query })
}

function goWorldBuilder() {
  const query = currentTask.value?.world_id ? { worldId: currentTask.value.world_id } : {}
  router.push({ name: 'WorldBuilder', query })
}

onMounted(() => {
  window.addEventListener(TASK_DELETED_EVENT, handleExternalTaskDeleted)
  window.addEventListener(TASK_SYNC_EVENT, handleTaskSync)
  loadInitialTask()
})
onBeforeUnmount(() => {
  window.removeEventListener(TASK_DELETED_EVENT, handleExternalTaskDeleted)
  window.removeEventListener(TASK_SYNC_EVENT, handleTaskSync)
  clearTimeout(timer)
  stopUiTicker()
})
</script>

<style scoped>
.extract-floating-root {
  position: fixed;
  right: 20px;
  bottom: 84px;
  z-index: 9998;
  font-family: var(--font-sans);
}

.extract-mini-btn {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  border: 1px solid var(--wf-border-light);
  background: rgba(17, 17, 19, 0.96);
  color: var(--wf-text-primary);
  cursor: pointer;
  box-shadow: var(--shadow-lg);
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.extract-mini-icon {
  display: flex;
  align-items: center;
  justify-content: center;
}

.extract-mini-pulse {
  position: absolute;
  top: -2px;
  right: -2px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #3b82f6;
  animation: extractPulse 1.6s infinite;
}

.extract-window {
  width: 360px;
  border: 1px solid var(--wf-border-light);
  border-radius: var(--radius-xl);
  background: rgba(17, 17, 19, 0.96);
  color: var(--wf-text-primary);
  box-shadow: var(--shadow-lg);
  overflow: hidden;
  backdrop-filter: blur(18px);
}

.extract-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid var(--wf-border);
}

.extract-kicker {
  font-size: 11px;
  color: var(--wf-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.extract-header h3 {
  margin: 2px 0 0;
  font-size: 16px;
}

.extract-icon-btn {
  width: 30px;
  height: 30px;
  border: 0;
  border-radius: var(--radius-sm);
  background: rgba(255,255,255,0.06);
  color: var(--wf-text-primary);
  cursor: pointer;
}

.extract-body {
  padding: 16px;
}

.extract-status-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.extract-status {
  padding: 3px 9px;
  border-radius: var(--radius-full);
  background: rgba(59, 130, 246, 0.12);
  color: #93c5fd;
  font-size: 12px;
}

.extract-status.is-paused,
.extract-status.is-stale,
.extract-status.is-cancelled {
  background: rgba(245, 158, 11, 0.12);
  color: #fbbf24;
}

.extract-percent {
  font-family: var(--font-mono);
  color: var(--wf-accent);
}

.extract-progress-bar {
  height: 8px;
  border-radius: 999px;
  background: var(--wf-bg-input);
  overflow: hidden;
}

.extract-progress-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #3b82f6, #10b981);
  transition: width var(--transition-normal);
}

.extract-message {
  color: var(--wf-text-secondary);
  font-size: 13px;
  line-height: 1.6;
}

.extract-complete-note,
.extract-estimate-note,
.extract-live-note {
  margin: -2px 0 10px;
  font-size: 12px;
  line-height: 1.5;
}

.extract-complete-note {
  padding: 8px 10px;
  border: 1px solid rgba(16, 185, 129, 0.28);
  border-radius: var(--radius-md);
  background: rgba(16, 185, 129, 0.10);
  color: #86efac;
  font-weight: 600;
}

.extract-estimate-note {
  color: var(--wf-text-secondary);
}

.extract-live-note {
  display: flex;
  align-items: center;
  gap: 7px;
  color: var(--wf-accent);
}

.extract-live-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--wf-accent);
  box-shadow: 0 0 9px var(--wf-accent-glow);
  animation: extractPulse 1.4s infinite;
  flex: 0 0 auto;
}

.extract-meta-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.extract-meta-grid div,
.extract-summary,
.extract-discoveries {
  padding: 9px;
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-md);
  background: rgba(255,255,255,0.035);
}

.extract-meta-grid span,
.extract-section-title {
  display: block;
  color: var(--wf-text-muted);
  font-size: 11px;
  margin-bottom: 4px;
}

.extract-meta-grid strong {
  color: var(--wf-text-primary);
  font-size: 13px;
}

.extract-discoveries,
.extract-summary {
  margin-top: 10px;
}

.extract-discoveries ul {
  margin: 0;
  padding-left: 18px;
  color: var(--wf-text-secondary);
  font-size: 13px;
}

.extract-summary p {
  margin: 0;
  color: var(--wf-text-secondary);
  font-size: 13px;
  line-height: 1.6;
  max-height: 84px;
  overflow: auto;
}

.extract-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 14px;
}

.extract-action-btn {
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-sm);
  background: rgba(255,255,255,0.06);
  color: var(--wf-text-primary);
  padding: 7px 10px;
  cursor: pointer;
  min-height: 32px;
}

.extract-action-btn.primary {
  background: var(--wf-accent);
  color: var(--wf-text-on-accent);
}

.extract-action-btn.danger {
  color: var(--wf-danger);
  border-color: rgba(255, 71, 87, 0.24);
}

.extract-action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@keyframes extractPulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.45); opacity: 0.55; }
}
</style>
