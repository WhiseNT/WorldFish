<template>
  <div class="rag-page">
    <!-- Header -->
    <header class="rag-header">
      <div class="header-content">
        <h1 class="rag-title">RAG 知识库</h1>
        <p class="rag-subtitle">向量语义检索 — 为世界观构建长期记忆知识库</p>
      </div>
      <div class="header-actions">
        <div class="world-selector">
          <label class="selector-label">世界观</label>
          <select v-model="selectedWorldId" @change="onWorldChange" class="world-select">
            <option value="">-- 选择世界观 --</option>
            <option v-for="w in worlds" :key="w.id" :value="w.id">{{ w.name || '未命名' }}</option>
          </select>
        </div>
        <button
          v-if="selectedWorldId"
          @click="confirmClear"
          :disabled="clearing"
          class="btn btn-accent"
        >
          {{ clearing ? '清空中...' : '清空知识库' }}
        </button>
      </div>
    </header>

    <!-- No world selected -->
    <div v-if="!selectedWorldId" class="empty-state">
      <div class="empty-icon"><SvgIcon name="book" :size="42" :stroke-width="1.6" /></div>
      <h3>选择世界观以管理知识库</h3>
      <p>RAG 知识库为每个世界观建立独立的向量索引，基于 Embedding 实现语义检索。</p>
    </div>

    <!-- World selected -->
    <template v-else>
      <!-- Stats Bar -->
      <div class="stats-bar">
        <div class="stat-item">
          <span class="stat-value">{{ stats.document_count }}</span>
          <span class="stat-label">文档总数</span>
        </div>
        <div class="stat-item">
          <span class="stat-value">{{ stats.collection_name }}</span>
          <span class="stat-label">集合名称</span>
        </div>
        <div class="stat-item">
          <span class="stat-value" :class="{ 'stat-active': stats.has_documents }">
            {{ stats.has_documents ? '已就绪' : '空' }}
          </span>
          <span class="stat-label">状态</span>
        </div>
      </div>

      <!-- Tabs -->
      <div class="tabs">
        <button :class="{ active: activeTab === 'add' }" @click="activeTab = 'add'" class="tab-button">
          添加文档
        </button>
        <button :class="{ active: activeTab === 'search' }" @click="activeTab = 'search'" class="tab-button">
          语义检索
        </button>
        <button :class="{ active: activeTab === 'list' }" @click="activeTab = 'list'; fetchDocuments()" class="tab-button">
          文档列表
        </button>
      </div>

      <!-- Tab: Add Documents -->
      <div v-if="activeTab === 'add'" class="tab-content fade-in">
        <div class="card">
          <h3 class="card-title">添加文本到知识库</h3>
          <div class="form-group">
            <label>文本来源</label>
            <select v-model="addSource" class="form-select">
              <option value="manual">手动输入</option>
              <option value="extraction">AI 提取</option>
              <option value="file">文件导入</option>
            </select>
          </div>
          <!-- 文件上传区域 -->
          <div v-if="addSource === 'file'" class="upload-area">
            <div
              class="upload-dropzone"
              @dragover.prevent
              @drop.prevent="onFileDrop"
              @click="fileInput?.click()"
            >
              <div class="upload-icon"><SvgIcon name="folder" :size="38" :stroke-width="1.6" /></div>
              <p v-if="pendingFiles.length === 0">点击或拖拽文件到此处上传</p>
              <p class="upload-hint">支持 PDF、Markdown、TXT 文件</p>
            </div>
            <input
              ref="fileInput"
              type="file"
              multiple
              accept=".pdf,.md,.markdown,.txt"
              @change="onFileSelect"
              hidden
            />
            <div v-if="pendingFiles.length > 0" class="upload-file-list">
              <div v-for="(f, i) in pendingFiles" :key="i" class="upload-file-item">
                <span class="upload-file-name"><SvgIcon name="file" :size="15" /> {{ f.name }}</span>
                <span class="upload-file-size">{{ formatSize(f.size) }}</span>
                <button class="upload-file-remove" @click="removeFile(i)" title="移除文件">
                  <SvgIcon name="close" :size="13" />
                </button>
              </div>
            </div>
          </div>

          <!-- 文本输入区域 -->
          <div v-else class="form-group">
            <label>文本内容 *</label>
            <textarea
              v-model="addText"
              placeholder="输入要添加到知识库的文本...&#10;&#10;长文本将按段落智能切分为多个文档块。"
              rows="10"
              class="form-textarea"
            ></textarea>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>切分预设</label>
              <select v-model="chunkPreset" class="form-select">
                <option v-for="preset in chunkPresets" :key="preset.id" :value="preset.id">
                  {{ preset.name }}
                </option>
              </select>
              <span class="form-hint">{{ selectedPresetDescription }}</span>
            </div>
            <div class="form-group">
              <label>切块大小（字符）</label>
              <input v-model.number="chunkSize" type="number" min="100" max="4000" class="form-input" />
            </div>
            <div class="form-group">
              <label>检索 Top-K</label>
              <input v-model.number="topK" type="number" min="1" max="50" class="form-input" />
            </div>
          </div>
          <div class="card-footer">
            <button
              @click="addToRag"
              :disabled="(addSource !== 'file' && !addText.trim()) || (addSource === 'file' && pendingFiles.length === 0) || adding"
              class="btn btn-primary"
            >
              {{ adding ? '处理中...' : (addSource === 'file' ? '上传并添加到知识库' : '添加到知识库') }}
            </button>
            <span v-if="addResult && !adding" class="add-result" :class="addResult.success ? 'message-success' : 'message-error'">
              {{ addResult.message }}
            </span>
          </div>

          <!-- Embedding 进度条 -->
          <div v-if="adding && embedProgress.message" class="embed-progress">
            <div class="progress-bar-container">
              <div class="progress-bar-fill" :style="{ width: embedProgress.progress + '%' }"></div>
            </div>
            <div class="progress-info">
              <span class="progress-stage">{{ embedProgress.message }}</span>
              <span class="progress-pct">{{ embedProgress.progress }}%</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Tab: Search -->
      <div v-if="activeTab === 'search'" class="tab-content fade-in">
        <div class="card">
          <h3 class="card-title">语义检索</h3>
          <div class="search-bar">
            <input
              v-model="searchQuery"
              @keyup.enter="doSearch"
              placeholder="输入查询，如：这个世界的魔法体系是怎样的？"
              class="search-input"
            />
            <button @click="doSearch" :disabled="!searchQuery.trim() || searching" class="btn btn-primary">
              {{ searching ? '检索中...' : '检索' }}
            </button>
          </div>
          <div class="form-row mt-md">
            <div class="form-group">
              <label>返回条数</label>
              <input v-model.number="searchTopK" type="number" min="1" max="50" class="form-input form-input-sm" />
            </div>
            <div class="form-group">
              <label>来源过滤</label>
              <select v-model="searchSource" class="form-select form-select-sm">
                <option value="">全部</option>
                <option value="manual">手动输入</option>
                <option value="extraction">AI 提取</option>
                <option value="file">文件导入</option>
              </select>
            </div>
          </div>
        </div>

        <!-- Results -->
        <div v-if="searchResults.length > 0" class="search-results mt-lg">
          <h3 class="results-title">检索结果 ({{ searchResults.length }})</h3>
          <div v-for="(r, i) in searchResults" :key="r.doc_id" class="result-item card">
            <div class="result-header">
              <span class="result-rank">#{{ i + 1 }}</span>
              <span class="tag tag-primary">{{ (r.score * 100).toFixed(1) }}% 相关</span>
              <span class="tag tag-accent">来源: {{ r.metadata?.source || '未知' }}</span>
              <span class="result-id">{{ r.doc_id }}</span>
            </div>
            <p class="result-text">{{ r.text }}</p>
          </div>
        </div>
        <div v-else-if="searchDone" class="empty-state mt-lg">
          <p>未找到相关结果</p>
        </div>
      </div>

      <!-- Tab: Document List -->
      <div v-if="activeTab === 'list'" class="tab-content fade-in">
        <div class="card">
          <h3 class="card-title">文档列表 ({{ stats.document_count }} 条)</h3>
          <div v-if="documents.length > 0" class="doc-list">
            <div v-for="doc in documents" :key="doc.doc_id" class="doc-item">
              <div class="doc-meta">
                <span class="doc-id">{{ doc.doc_id }}</span>
                <span class="tag tag-accent">{{ doc.metadata?.source || '未知' }}</span>
                <span class="doc-length">{{ doc.text_length }} 字符</span>
              </div>
              <p class="doc-text">{{ doc.text }}</p>
              <button @click="deleteDocument(doc.doc_id)" class="btn-text btn-text-danger">删除</button>
            </div>
          </div>
          <div v-else class="doc-empty">
            <p>知识库暂无文档</p>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { worldApi } from '../api/world'
import { ragApi } from '../api/rag'
import SvgIcon from '../components/ui/SvgIcon.vue'

const route = useRoute()

// ============== State ==============
const worlds = ref([])
const selectedWorldId = ref('')
const activeTab = ref('add')
const stats = ref({ document_count: 0, collection_name: '', has_documents: false })

// Add tab
const addText = ref('')
const addSource = ref('manual')
const chunkSize = ref(800)
const chunkPreset = ref('novel')
const chunkPresets = ref([
  { id: 'novel', name: '小说章节', description: '优先按“第X章”等章节标题切分，超长章节自动再切块。' },
  { id: 'default', name: '通用段落', description: '按段落和句子边界切分。' },
])
const selectedPresetDescription = computed(() => chunkPresets.value.find(p => p.id === chunkPreset.value)?.description || '')
const topK = ref(5)
const adding = ref(false)
const addResult = ref(null)
const pendingFiles = ref([])
const embedProgress = ref({ stage: '', progress: 0, message: '', detail: {} })
let embedProgressRealTimer = null

// Search tab
const searchQuery = ref('')
const searchTopK = ref(5)
const searchSource = ref('')
const searching = ref(false)
const searchResults = ref([])
const searchDone = ref(false)

// List tab
const documents = ref([])

// Clear
const clearing = ref(false)
const fileInput = ref(null)

// ============== Methods ==============
async function fetchWorlds() {
  try {
    const res = await worldApi.listWorlds()
    worlds.value = res.worlds || []
  } catch (e) {
    console.error('加载世界观列表失败:', e)
  }
}

async function fetchStats() {
  if (!selectedWorldId.value) return
  try {
    const res = await ragApi.getStats(selectedWorldId.value)
    stats.value = res.data || stats.value
  } catch (e) {
    console.error('加载 RAG 统计失败:', e)
  }
}

async function fetchChunkPresets() {
  try {
    const res = await ragApi.getChunkPresets()
    const presets = res.data?.presets || []
    if (presets.length > 0) {
      chunkPresets.value = presets
      chunkPreset.value = presets.find(p => p.default)?.id || presets[0].id
    }
  } catch (e) {
    console.warn('加载切分预设失败，使用默认预设:', e)
  }
}

function onWorldChange() {
  stats.value = { document_count: 0, collection_name: '', has_documents: false }
  searchResults.value = []
  searchDone.value = false
  addResult.value = null
  documents.value = []
  if (selectedWorldId.value) {
    fetchStats()
  }
}

// ============== Embedding 真实进度轮询 ==============
function clearEmbedTimers() {
  if (embedProgressRealTimer) { clearInterval(embedProgressRealTimer); embedProgressRealTimer = null }
}

function updateEmbedProgress(progress, message, stage = 'processing', detail = {}) {
  embedProgress.value = {
    stage,
    progress: Math.max(0, Math.min(Math.round(progress || 0), 100)),
    message,
    detail,
  }
}

function finishEmbedProgress(success, message) {
  clearEmbedTimers()
  if (success) {
    updateEmbedProgress(100, message || 'Embedding 完成，知识库已更新', 'done')
  }
}

function pollIndexTask(taskId) {
  clearEmbedTimers()
  return new Promise((resolve, reject) => {
    embedProgressRealTimer = setInterval(async () => {
      try {
        const res = await ragApi.getIndexTask(selectedWorldId.value, taskId)
        const task = res.data || {}
        updateEmbedProgress(task.progress || 0, task.message || '正在索引...', task.stage || 'processing', task.detail || {})
        if (task.done) {
          clearEmbedTimers()
          if (task.error) reject(new Error(task.error))
          else resolve(task.result || {})
        }
      } catch (e) {
        clearEmbedTimers()
        reject(e)
      }
    }, 700)
  })
}

// Add
async function addToRag() {
  // File upload mode
  if (addSource.value === 'file') {
    if (pendingFiles.value.length === 0) return
    adding.value = true
    addResult.value = null
    updateEmbedProgress(3, '正在上传文件并准备索引...', 'uploading')
    try {
      const res = await ragApi.uploadFile(
        selectedWorldId.value,
        pendingFiles.value,
        chunkSize.value || undefined,
        Math.floor((chunkSize.value || 800) / 8),
        chunkPreset.value,
      )
      const r = res.data
      const ok = r.results.filter(f => f.success)
      const fail = r.results.filter(f => !f.success)
      let msg = `成功上传 ${ok.length} 个文件，添加 ${r.total_added} 个文档块。知识库现有 ${r.total_count} 条。`
      if (fail.length > 0) msg += ` ${fail.length} 个文件失败。`
      addResult.value = { success: ok.length > 0, message: msg }
      finishEmbedProgress(ok.length > 0)
      pendingFiles.value = []
      fetchStats()
    } catch (e) {
      addResult.value = { success: false, message: '上传失败: ' + (e.message || '未知错误') }
      finishEmbedProgress(false)
    } finally {
      adding.value = false
    }
    return
  }

  // Text input mode
  if (!addText.value.trim()) return
  adding.value = true
  addResult.value = null

  updateEmbedProgress(1, '正在创建索引任务...', 'queued')

  try {
    const taskRes = await ragApi.createIndexTask(selectedWorldId.value, {
      text: addText.value.trim(),
      chunk_size: chunkSize.value || undefined,
      chunk_overlap: Math.floor((chunkSize.value || 800) / 8),
      chunk_preset: chunkPreset.value,
      source: addSource.value,
    })
    const taskId = taskRes.data?.task_id
    if (!taskId) throw new Error('索引任务创建失败')
    const result = await pollIndexTask(taskId)
    addResult.value = {
      success: true,
      message: `成功添加 ${result.added_count || 0} 个文档块，知识库现有 ${result.total_count || 0} 条`,
    }
    finishEmbedProgress(true)
    addText.value = ''
    fetchStats()
  } catch (e) {
    addResult.value = { success: false, message: '添加失败: ' + (e.message || '未知错误') }
    finishEmbedProgress(false)
  } finally {
    adding.value = false
  }
}

// File handlers
function onFileSelect(e) {
  const files = Array.from(e.target.files || [])
  pendingFiles.value.push(...files)
  e.target.value = ''
}

function onFileDrop(e) {
  const files = Array.from(e.dataTransfer.files || [])
  pendingFiles.value.push(...files)
}

function removeFile(idx) {
  pendingFiles.value.splice(idx, 1)
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

// Search
async function doSearch() {
  if (!searchQuery.value.trim()) return
  searching.value = true
  searchResults.value = []
  searchDone.value = false
  try {
    const payload = { query: searchQuery.value.trim(), top_k: searchTopK.value || undefined }
    if (searchSource.value) payload.source = searchSource.value
    const res = await ragApi.search(selectedWorldId.value, payload)
    searchResults.value = res.data.results || []
  } catch (e) {
    console.error('检索失败:', e)
  } finally {
    searching.value = false
    searchDone.value = true
  }
}

// List
async function fetchDocuments() {
  if (!selectedWorldId.value) return
  try {
    const res = await ragApi.listDocuments(selectedWorldId.value, { limit: 100, offset: 0 })
    documents.value = res.data.documents || []
  } catch (e) {
    console.error('加载文档列表失败:', e)
  }
}

// Delete
async function deleteDocument(docId) {
  try {
    await ragApi.deleteDocument(selectedWorldId.value, docId)
    documents.value = documents.value.filter(d => d.doc_id !== docId)
    fetchStats()
  } catch (e) {
    console.error('删除文档失败:', e)
  }
}

// Clear
async function confirmClear() {
  if (!confirm('确定要清空该世界观的全部知识库文档吗？此操作不可撤销。')) return
  clearing.value = true
  try {
    await ragApi.clear(selectedWorldId.value)
    stats.value = { document_count: 0, collection_name: stats.value.collection_name, has_documents: false }
    documents.value = []
    searchResults.value = []
  } catch (e) {
    console.error('清空知识库失败:', e)
  } finally {
    clearing.value = false
  }
}

onMounted(async () => {
  await fetchChunkPresets()
  await fetchWorlds()
  // 从 URL query 参数读取 worldId（从 Home 页导航而来）
  const queryWorldId = route.query.worldId
  if (queryWorldId && worlds.value.some(w => w.id === queryWorldId)) {
    selectedWorldId.value = queryWorldId
    onWorldChange()
  }
})
</script>

<style scoped>
.rag-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--spacing-2xl) var(--spacing-lg);
}

/* Header */
.rag-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-xl);
  padding-bottom: var(--spacing-lg);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  flex-wrap: wrap;
}

.rag-title {
  font-family: var(--font-display);
  font-size: 2rem;
  font-weight: 700;
  color: var(--wf-text-primary);
  letter-spacing: 1px;
}

.rag-subtitle {
  font-size: 0.95rem;
  color: var(--wf-text-secondary);
  margin-top: var(--spacing-xs);
}

.header-actions {
  display: flex;
  align-items: flex-end;
  gap: var(--spacing-md);
}

.world-selector {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.selector-label {
  font-size: 13px;
  color: var(--wf-text-muted);
  font-weight: 500;
}

.world-select {
  background: var(--wf-bg-input);
  color: var(--wf-text-primary);
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-md);
  padding: var(--spacing-sm) var(--spacing-md);
  font-size: 14px;
  font-family: var(--font-sans);
  min-width: 240px;
}

.world-select:focus {
  outline: none;
  border-color: var(--wf-accent);
  box-shadow: 0 0 0 3px var(--wf-accent-muted);
}

/* Stats Bar */
.stats-bar {
  display: flex;
  gap: var(--spacing-xl);
  margin-bottom: var(--spacing-lg);
  padding: var(--spacing-md) var(--spacing-lg);
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-lg);
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat-value {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--wf-text-primary);
  font-family: var(--font-mono);
}

.stat-active {
  color: var(--wf-success);
}

.stat-label {
  font-size: 12px;
  color: var(--wf-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Card */
.card-title {
  font-size: 1.05rem;
  font-weight: 600;
  color: var(--wf-text-primary);
  margin-bottom: var(--spacing-md);
}

.card-footer {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  margin-top: var(--spacing-md);
}

/* Forms */
.form-select, .form-input {
  width: 100%;
  background: var(--wf-bg-input);
  color: var(--wf-text-primary);
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-md);
  padding: var(--spacing-sm) var(--spacing-md);
  font-size: 14px;
  font-family: var(--font-sans);
}

.form-select:focus, .form-input:focus {
  outline: none;
  border-color: var(--wf-accent);
  box-shadow: 0 0 0 3px var(--wf-accent-muted);
}

.form-input-sm {
  max-width: 120px;
}

.form-select-sm {
  max-width: 160px;
}

.form-hint {
  display: block;
  margin-top: 6px;
  font-size: 12px;
  color: var(--wf-text-muted);
  line-height: 1.4;
}

.form-textarea {
  width: 100%;
  background: var(--wf-bg-input);
  color: var(--wf-text-primary);
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  font-size: 14px;
  font-family: var(--font-sans);
  resize: vertical;
  line-height: 1.6;
}

.form-textarea:focus {
  outline: none;
  border-color: var(--wf-accent);
  box-shadow: 0 0 0 3px var(--wf-accent-muted);
}

.form-textarea::placeholder {
  color: var(--wf-text-muted);
}

/* Add result */
.add-result {
  font-size: 13px;
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-sm);
}

/* Search */
.search-bar {
  display: flex;
  gap: var(--spacing-md);
}

.search-input {
  flex: 1;
  background: var(--wf-bg-input);
  color: var(--wf-text-primary);
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-md);
  padding: var(--spacing-sm) var(--spacing-md);
  font-size: 15px;
  font-family: var(--font-sans);
}

.search-input:focus {
  outline: none;
  border-color: var(--wf-accent);
  box-shadow: 0 0 0 3px var(--wf-accent-muted);
}

.search-input::placeholder {
  color: var(--wf-text-muted);
}

.results-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--wf-text-primary);
  margin-bottom: var(--spacing-md);
}

.result-item {
  margin-bottom: var(--spacing-md);
}

.result-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-sm);
  flex-wrap: wrap;
}

.result-rank {
  font-family: var(--font-mono);
  font-size: 13px;
  color: var(--wf-accent);
  font-weight: 600;
}

.result-id {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--wf-text-muted);
  margin-left: auto;
}

.result-text {
  font-size: 0.9rem;
  color: var(--wf-text-secondary);
  line-height: 1.7;
  white-space: pre-wrap;
}

/* Document List */
.doc-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.doc-item {
  padding: var(--spacing-md);
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-md);
}

.doc-meta {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-sm);
  flex-wrap: wrap;
}

.doc-id {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--wf-text-muted);
}

.doc-length {
  font-size: 12px;
  color: var(--wf-text-muted);
}

.doc-text {
  font-size: 0.85rem;
  color: var(--wf-text-secondary);
  line-height: 1.6;
  margin-bottom: var(--spacing-sm);
}

.doc-empty {
  text-align: center;
  padding: var(--spacing-xl);
  color: var(--wf-text-muted);
}

/* Text button */
.btn-text {
  background: none;
  border: none;
  font-size: 13px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
}

.btn-text-danger {
  color: var(--wf-danger);
}

.btn-text-danger:hover {
  background: rgba(255, 71, 87, 0.1);
}

/* Empty */
.empty-state {
  text-align: center;
  padding: var(--spacing-2xl) var(--spacing-lg);
  border: 1px dashed var(--wf-border);
  border-radius: var(--radius-xl);
  background: rgba(255, 255, 255, 0.02);
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: var(--spacing-md);
}

.empty-state h3 {
  color: var(--wf-text-primary);
  margin-bottom: var(--spacing-sm);
}

.empty-state p {
  color: var(--wf-text-secondary);
  max-width: 480px;
  margin: 0 auto;
  font-size: 0.95rem;
  line-height: 1.6;
}

/* File upload */
.upload-area {
  margin-bottom: var(--spacing-md);
}
.upload-dropzone {
  border: 2px dashed rgba(255, 255, 255, 0.12);
  border-radius: var(--radius-lg);
  padding: var(--spacing-xl) var(--spacing-lg);
  text-align: center;
  cursor: pointer;
  transition: all var(--transition-fast);
  background: rgba(255, 255, 255, 0.02);
}
.upload-dropzone:hover {
  border-color: var(--wf-accent);
  background: rgba(255, 255, 175, 0.04);
}
.upload-icon {
  font-size: 2.5rem;
  margin-bottom: var(--spacing-sm);
}
.upload-hint {
  font-size: 12px;
  color: var(--wf-text-muted);
  margin-top: var(--spacing-xs);
}
.upload-file-list {
  margin-top: var(--spacing-sm);
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.upload-file-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: var(--radius-md);
  font-size: 13px;
}
.upload-file-name {
  flex: 1;
  color: var(--wf-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.upload-file-size {
  color: var(--wf-text-muted);
  font-size: 12px;
  flex-shrink: 0;
}
.upload-file-remove {
  background: none;
  border: none;
  color: var(--wf-text-muted);
  cursor: pointer;
  font-size: 16px;
  padding: 0 4px;
  flex-shrink: 0;
  transition: color var(--transition-fast);
}
.upload-file-remove:hover {
  color: var(--wf-danger);
}

/* Tabs override */
.tabs {
  margin-bottom: var(--spacing-lg);
}

.tab-content {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Embedding Progress Bar */
.embed-progress {
  margin-top: var(--spacing-md);
}

.progress-bar-container {
  width: 100%;
  height: 8px;
  background: var(--wf-bg-hover, #2a2a35);
  border-radius: 4px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--wf-accent, #3b82f6), #6366f1);
  border-radius: 4px;
  transition: width 0.3s ease;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: var(--spacing-xs);
}

.progress-stage {
  font-size: 0.85rem;
  color: var(--wf-text-secondary);
}

.progress-pct {
  font-size: 0.8rem;
  color: var(--wf-accent);
  font-weight: 600;
  font-family: var(--font-mono);
}

/* Responsive */
@media (max-width: 768px) {
  .rag-header {
    flex-direction: column;
  }
  .header-actions {
    width: 100%;
    flex-wrap: wrap;
  }
  .world-select {
    min-width: 100%;
  }
  .stats-bar {
    flex-wrap: wrap;
    gap: var(--spacing-md);
  }
}
</style>
