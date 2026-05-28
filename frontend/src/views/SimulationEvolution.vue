<template>
  <div class="evo-page">
    <div class="evo-header">
      <StepIndicator
        :currentStep="status === 'completed' ? 3 : 2"
        :totalSteps="3"
        :stepLabels="['推演设置', '推演进化', '结果']"
      />
      <div class="evo-header-right">
        <span v-if="evoType === 'branch'" class="tag tag-accent">重新推演</span>
        <span v-else class="tag tag-primary">向后推演</span>
        <button v-if="status === 'completed'" class="btn btn-accent btn-sm" @click="showApplyDialog = true">
          变更实体
        </button>
      </div>
    </div>

    <div v-if="loading" class="state-box"><div class="loading-spinner"></div><p>加载中...</p></div>
    <div v-else-if="loadError" class="state-box"><p class="message-error">{{ loadError }}</p></div>

    <div v-else class="evo-layout">
      <!-- 左：知识图谱 -->
      <div class="evo-graph-panel">
        <GraphPanel
          v-if="graphData"
          :graphData="graphData"
          :loading="false"
          :currentPhase="2"
          :isSimulating="false"
          @refresh="loadGraph"
          @toggle-maximize="toggleGraphMax"
          @entity-click="onEntityClick"
        />
        <div v-else class="graph-placeholder">{{ graphLoading ? '图谱加载中...' : graphMessage }}</div>
      </div>

      <!-- 右：推演轮次 -->
      <div class="evo-right">
        <div class="evo-meta card">
          <div class="evo-meta-grid">
            <div class="meta-block is-wide">
              <span class="meta-label">推演场景</span>
              <p class="meta-value">{{ evolutionScenario || '未提供推演场景。' }}</p>
            </div>
            <div class="meta-block">
              <span class="meta-label">当前状态</span>
              <p class="meta-value">{{ statusText }}</p>
            </div>
            <div class="meta-block">
              <span class="meta-label">时间锚点</span>
              <p class="meta-value">{{ resolvedAnchorText }}</p>
            </div>
            <div class="meta-block">
              <span class="meta-label">关注领域</span>
              <p class="meta-value">{{ focusAreaText }}</p>
            </div>
            <div class="meta-block">
              <span class="meta-label">创意温度</span>
              <p class="meta-value">{{ evolutionTemperatureText }}</p>
            </div>
          </div>
        </div>

        <div v-if="isActiveEvolution" class="inline-status card">
          <div class="loading-spinner"></div>
          <div class="inline-status-main">
            <h4>{{ activeStatusTitle }}</h4>
            <p>{{ activeStatusMessage }}</p>
            <div class="inline-progress-meta">
              <span>进度 {{ safeCurrentRound }} / {{ safeTotalRounds }} 轮</span>
              <span>{{ progressPercent }}%</span>
            </div>
            <div class="progress-bar compact"><div class="progress-fill" :style="{ width: progressPercent + '%' }"></div></div>
            <p v-if="lastNarrative" class="last-narrative">最新进展：{{ lastNarrative }}</p>
          </div>
        </div>

        <div v-if="consolidationSummary || (status === 'completed' && rounds.length)" class="result-summary card">
          <div class="result-summary-header">
            <h3>推演结果</h3>
            <span class="tag tag-accent">总结</span>
          </div>
          <p class="result-summary-text">{{ resultSummaryText }}</p>

          <div v-if="consolidationSummary.key_themes?.length" class="result-chip-list">
            <span v-for="theme in consolidationSummary.key_themes" :key="theme" class="tag tag-primary">{{ theme }}</span>
          </div>

          <div v-if="consolidationSummary.inconsistencies?.length" class="result-section">
            <h4>一致性提示</h4>
            <ul class="result-list">
              <li v-for="item in consolidationSummary.inconsistencies" :key="item">{{ item }}</li>
            </ul>
          </div>

          <div v-if="consolidationSummary.timeline?.length" class="result-section">
            <h4>推演时间线</h4>
            <div class="result-timeline">
              <div v-for="(item, index) in consolidationSummary.timeline" :key="`${index}-${item.time || item.event}`" class="timeline-item">
                <span class="timeline-time">{{ item.time || '未知时间' }}</span>
                <span class="timeline-event">{{ item.event || '未命名事件' }}</span>
              </div>
            </div>
          </div>

          <div v-if="consolidationSummary.final_entity_states?.length" class="result-section">
            <h4>最终角色状态</h4>
            <div class="final-state-list">
              <article v-for="item in consolidationSummary.final_entity_states" :key="item.name" class="final-state-card">
                <div class="final-state-main">
                  <h5>{{ item.name }}</h5>
                  <p>{{ item.final_status }}</p>
                </div>
                <button class="btn btn-secondary btn-xs" @click="openEvolutionEntityChat(item.name)">对话</button>
              </article>
            </div>
          </div>
        </div>

        <div v-if="isActiveEvolution" class="progress-section">
          <div class="progress-info">
            <span>第 {{ safeCurrentRound }} / {{ safeTotalRounds }} 轮</span>
            <span class="progress-pct">{{ progressPercent }}%</span>
          </div>
          <div class="progress-bar"><div class="progress-fill" :style="{ width: progressPercent + '%' }"></div></div>
        </div>

        <div class="rounds-scroll">
          <div v-for="round in rounds" :key="round.round_number" class="round-card card fade-in">
            <div class="round-header">
              <span class="round-badge">第 {{ round.round_number }} 轮</span>
              <span v-if="round.year_advanced_to" class="round-year">{{ round.year_advanced_to }}</span>
            </div>
            <div class="round-narrative">{{ round.narrative }}</div>

            <div v-if="round.affected_entities?.length" class="round-entities">
              <h4>变化的实体</h4>
              <div v-for="ent in round.affected_entities" :key="ent.name" class="entity-change">
                <span class="ent-name">{{ ent.name }}</span>
                <span class="tag tag-primary">{{ ent.new_status }}</span>
              </div>
            </div>

            <div v-if="round.new_events?.length" class="round-events">
              <h4>新事件</h4>
              <div v-for="evt in round.new_events" :key="evt.name" class="mini-event">
                <span class="evt-name">{{ evt.name }}</span>
                <span v-if="evt.date" class="evt-date">{{ evt.date }}</span>
              </div>
            </div>

            <div class="round-actions">
              <button class="btn btn-secondary btn-xs" @click="startBranchFrom(round.round_number)">从此轮重新推演</button>
            </div>
          </div>

          <div v-if="rounds.length === 0 && isActiveEvolution" class="state-box">
            <div class="loading-spinner"></div><p>{{ status === 'planning' ? '正在规划第一轮...' : '正在生成第一轮...' }}</p>
          </div>

          <div v-if="status === 'completed' && rounds.length === 0" class="state-box">
            <p class="message-warning">推演已结束，但暂未返回可展示的轮次内容。</p>
          </div>

          <!-- 向后推演 -->
          <div v-if="status === 'completed'" class="forward-section card">
            <h4>向后推演 — 从当前终点继续</h4>
            <textarea v-model="forwardScenario" class="scenario-input" rows="2" placeholder="继续推演的场景..."></textarea>
            <div class="forward-params">
              <label>轮次 <input v-model.number="forwardRounds" type="number" min="1" max="10" /></label>
              <button class="btn btn-primary btn-sm" :disabled="!forwardScenario.trim() || forwarding" @click="startForward">
                <template v-if="forwarding">...</template>
                <template v-else><span>向后推演</span><SvgIcon name="arrow-right" :size="14" /></template>
              </button>
            </div>
          </div>
        </div>

        <div v-if="status === 'failed'" class="state-box"><p class="message-error">{{ loadError || '推演失败' }}</p></div>
      </div>
    </div>

    <!-- 变更实体弹窗 -->
    <div v-if="showApplyDialog" class="dialog-overlay" @click.self="showApplyDialog = false">
      <div class="dialog-content apply-dialog">
        <div class="dialog-header">
          <h2>变更实体 — 应用到世界观</h2>
          <button class="close-btn" @click="showApplyDialog = false" title="关闭"><SvgIcon name="close" :size="16" /></button>
        </div>
        <div class="dialog-body">
          <p class="hint">勾选你想应用的变更，它们将添加回世界观设定中</p>
          <div class="apply-list">
            <div v-for="round in rounds" :key="'apply-' + round.round_number" class="apply-round-group">
              <h5>第 {{ round.round_number }} 轮</h5>
              <label v-for="ent in (round.affected_entities || [])" :key="ent.name" class="apply-checkbox">
                <input type="checkbox" :value="{ round: round.round_number, name: ent.name, state_changes: ent.state_changes, new_status: ent.new_status }" v-model="selectedEntities" />
                <span class="apply-ent-name">{{ ent.name }}</span>
                <span class="apply-ent-change">{{ ent.state_changes }}</span>
              </label>
              <label v-for="evt in (round.new_events || [])" :key="'evt-' + evt.name" class="apply-checkbox">
                <input type="checkbox" :value="evt" v-model="selectedEvents" />
                <span class="apply-ent-name">事件: {{ evt.name }}</span>
                <span class="apply-ent-change">{{ evt.date }}</span>
              </label>
            </div>
          </div>
        </div>
        <div class="dialog-footer">
          <button class="btn btn-secondary" @click="showApplyDialog = false">取消</button>
          <button class="btn btn-accent" :disabled="(!selectedEntities.length && !selectedEvents.length) || applying" @click="applyChanges">
            {{ applying ? '应用中...' : `应用 (${selectedEntities.length} 实体, ${selectedEvents.length} 事件)` }}
          </button>
        </div>
        <p v-if="applyMsg" class="message-success">{{ applyMsg }}</p>
        <p v-if="applyErr" class="message-error">{{ applyErr }}</p>
      </div>
    </div>

    <!-- 实体对话弹窗 -->
    <div v-if="chatEntity" class="dialog-overlay" @click.self="chatEntity = null">
      <div class="dialog-content entity-chat-dialog">
        <div class="dialog-header">
          <h2>与 {{ chatEntity.name }} 对话</h2>
          <button class="close-btn" @click="chatEntity = null" title="关闭"><SvgIcon name="close" :size="16" /></button>
        </div>
        <div class="chat-profile-card">
          <div class="chat-profile-header" @click="chatProfileCollapsed = !chatProfileCollapsed" style="cursor: pointer; display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <span style="font-size: 0.9rem; font-weight: 500; color: var(--wf-text-primary);">人物小传</span>
            <span class="chat-profile-toggle-text">
              {{ chatProfileCollapsed ? '展开' : '折叠' }}
              <SvgIcon :name="chatProfileCollapsed ? 'chevron-down' : 'chevron-up'" :size="12" />
            </span>
          </div>
          <div v-show="!chatProfileCollapsed">
            <div v-if="chatProfileLoading" class="chat-profile-loading">正在生成当前角色小传...</div>
            <div v-if="chatProfileNotice" class="chat-profile-notice">{{ chatProfileNotice }}</div>
            <div class="chat-profile-meta">
              <span v-if="chatCurrentTime" class="tag tag-accent">{{ chatCurrentTime }}</span>
              <span v-if="chatCurrentStatus" class="tag tag-primary">{{ chatCurrentStatus }}</span>
            </div>
            <p class="chat-profile-text">{{ chatBrief || '暂无角色小传。' }}</p>
          </div>
        </div>
        <div class="chat-messages">
          <div v-for="(msg, i) in chatMessages" :key="i" :class="['chat-msg', msg.role]">{{ msg.content }}</div>
          <div v-if="chatLoading" class="chat-msg assistant">思考中...</div>
        </div>
        <div class="chat-input-row">
          <input v-model="chatInput" class="form-input chat-input" placeholder="输入你的问题..." @keyup.enter="sendChat" />
          <button class="btn btn-primary" :disabled="chatLoading" @click="sendChat">发送</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import StepIndicator from '../components/StepIndicator.vue'
import GraphPanel from '../components/GraphPanel.vue'
import SvgIcon from '../components/ui/SvgIcon.vue'
import { default as service } from '../api/index'

const route = useRoute()
const router = useRouter()
const evolutionId = ref(route.params.id)

const loading = ref(true)
const loadError = ref('')
const status = ref('running')
const worldId = ref('')
const rounds = ref([])
const currentRound = ref(0)
const totalRounds = ref(5)
const evoType = ref('forward')
const parentEvoId = ref('')
const evolutionScenario = ref('')
const evolutionConfig = ref({})
const consolidationSummary = ref(null)
const lastNarrative = ref('')
const latestWarnings = ref([])
const warningCount = ref(0)
let pollTimer = null

const activeStatuses = new Set(['created', 'planning', 'running', 'consolidating'])
const terminalStatuses = new Set(['completed', 'failed'])

const graphData = ref(null)
const graphLoading = ref(false)
const graphMessage = ref('暂无可用图谱数据。')
const showApplyDialog = ref(false)

const statusText = computed(() => ({
  created: '已创建，等待启动',
  planning: '正在规划',
  running: '正在推演',
  consolidating: '正在整合结果',
  completed: '已完成',
  failed: '推演失败',
})[status.value] || status.value || '未知状态')

const isActiveEvolution = computed(() => activeStatuses.has(status.value))
const safeTotalRounds = computed(() => Math.max(Number(totalRounds.value) || 1, 1))
const safeCurrentRound = computed(() => Math.min(Math.max(Number(currentRound.value) || 0, 0), safeTotalRounds.value))
const progressPercent = computed(() => Math.min(100, Math.max(0, Math.round((safeCurrentRound.value / safeTotalRounds.value) * 100))))
const activeStatusTitle = computed(() => ({
  created: '推演卡片已创建',
  planning: '正在规划推演阶段',
  running: '正在推演世界变化',
  consolidating: '正在整合推演结果',
})[status.value] || '正在推演')
const activeStatusMessage = computed(() => {
  if (status.value === 'created') return '后端任务已创建，正在等待推演引擎接手。'
  if (status.value === 'planning') return '正在根据你给定的时间/事件锚点拆分阶段。'
  if (status.value === 'consolidating') return '正在汇总关键主题、时间线与最终状态。'
  if (lastNarrative.value) return '推演正在进行，页面会持续同步最新轮次。'
  return '推演正在进行，正在等待第一轮内容生成。'
})

const resultSummaryText = computed(() => {
  if (consolidationSummary.value?.summary) return consolidationSummary.value.summary
  const latestRound = rounds.value?.[rounds.value.length - 1]
  if (latestRound?.narrative) return latestRound.narrative
  return '推演已完成，结果正在整理。'
})

const resolvedAnchorText = computed(() => {
  const anchor = evolutionConfig.value?.resolved_anchor || {}
  if (anchor.label) {
    return anchor.label
  }
  if (anchor.event_name) {
    return anchor.event_name
  }
  if (evolutionConfig.value?.time_span_start) {
    return evolutionConfig.value.time_span_start
  }
  return '未设置'
})

const focusAreaText = computed(() => {
  const items = Array.isArray(evolutionConfig.value?.focus_areas) ? evolutionConfig.value.focus_areas.filter(Boolean) : []
  return items.length ? items.join('、') : '未限定'
})

const evolutionTemperatureText = computed(() => {
  const value = evolutionConfig.value?.temperature
  return value === undefined || value === null || value === '' ? '默认' : String(value)
})

const normalizeGraphKey = (value = '') => String(value || '').trim().toLowerCase().replace(/[\s\-—_·•・()（）\[\]{}《》<>“”"'`]+/g, '')

const hasRenderableValue = (value) => {
  if (Array.isArray(value)) {
    return value.some(item => hasRenderableValue(item))
  }
  if (value && typeof value === 'object') {
    return Object.values(value).some(item => hasRenderableValue(item))
  }
  return Boolean(String(value ?? '').trim())
}

const formatGraphValue = (value) => {
  if (!hasRenderableValue(value)) {
    return ''
  }
  if (Array.isArray(value)) {
    return value.map(item => formatGraphValue(item)).filter(Boolean).join('；')
  }
  if (value && typeof value === 'object') {
    return Object.entries(value)
      .filter(([, nestedValue]) => hasRenderableValue(nestedValue))
      .map(([key, nestedValue]) => `${key}: ${formatGraphValue(nestedValue)}`)
      .filter(Boolean)
      .join('；')
  }
  return String(value ?? '').trim()
}

const buildEvolutionSnapshots = () => {
  const snapshots = new Map()

  for (const round of rounds.value || []) {
    for (const entity of round.affected_entities || []) {
      const name = String(entity?.name || '').trim()
      const key = normalizeGraphKey(name)
      if (!key) {
        continue
      }
      snapshots.set(key, {
        name,
        roundLabel: `第 ${round.round_number} 轮`,
        newStatus: String(entity?.new_status || '').trim(),
        stateChanges: String(entity?.state_changes || '').trim(),
      })
    }
  }

  for (const item of consolidationSummary.value?.final_entity_states || []) {
    const name = String(item?.name || '').trim()
    const key = normalizeGraphKey(name)
    if (!key || snapshots.has(key)) {
      continue
    }
    snapshots.set(key, {
      name,
      roundLabel: '推演总结',
      newStatus: String(item?.final_status || '').trim(),
      stateChanges: String(item?.final_status || '').trim(),
    })
  }

  return snapshots
}

async function loadGraph() {
  if (!worldId.value) return
  graphLoading.value = true
  graphMessage.value = '图谱加载中...'
  try {
    const res = await service.get(`/api/world/${worldId.value}`)
    const w = res.world || {}
    const nodes = []
    const edges = []
    const nodeByKey = new Map()
    const edgeKeys = new Set()
    const evolutionSnapshots = buildEvolutionSnapshots()

    const registerNodeKeys = (node, names = []) => {
      for (const rawName of names) {
        const key = normalizeGraphKey(rawName)
        if (key && !nodeByKey.has(key)) {
          nodeByKey.set(key, node)
        }
      }
    }

    const ensureReferenceNode = (name, options = {}) => {
      const displayName = String(name || '').trim()
      const key = normalizeGraphKey(displayName)
      if (!key) {
        return null
      }
      if (nodeByKey.has(key)) {
        return nodeByKey.get(key)
      }

      const snapshot = evolutionSnapshots.get(key)
      const attributes = {
        说明: options.summary || '该实体当前只在关系或推演结果中被引用。',
      }
      if (snapshot?.roundLabel) {
        attributes['推演轮次'] = snapshot.roundLabel
      }
      if (snapshot?.newStatus) {
        attributes['推演最新状态'] = snapshot.newStatus
      }
      if (snapshot?.stateChanges) {
        attributes['推演变化'] = snapshot.stateChanges
      }

      const node = {
        uuid: options.uuid || `ref-${nodes.length}`,
        name: displayName,
        labels: [options.label || '引用实体'],
        summary: options.summary || snapshot?.stateChanges || snapshot?.newStatus || '仅在关系或推演结果中被提及。',
        attributes,
        stages: [],
      }
      nodes.push(node)
      registerNodeKeys(node, [displayName])
      return node
    }

    for (const entity of w.entities || []) {
      const entityName = String(entity?.name || '').trim()
      if (!entityName) {
        continue
      }

      const snapshot = evolutionSnapshots.get(normalizeGraphKey(entityName))
      const displayAttributes = {}
      for (const [key, value] of Object.entries(entity.attributes || {})) {
        const formatted = formatGraphValue(value)
        if (formatted) {
          displayAttributes[key] = formatted
        }
      }
      if (snapshot?.roundLabel) {
        displayAttributes['推演轮次'] = snapshot.roundLabel
      }
      if (snapshot?.newStatus) {
        displayAttributes['推演最新状态'] = snapshot.newStatus
      }
      if (snapshot?.stateChanges) {
        displayAttributes['推演变化'] = snapshot.stateChanges
      }

      const summary = Object.entries(displayAttributes)
        .slice(0, 4)
        .map(([key, value]) => `${key}: ${value}`)
        .join('; ') || entityName

      const node = {
        uuid: entity.id || `ent-${nodes.length}`,
        name: entityName,
        labels: [entity.type || 'Entity'],
        summary,
        attributes: displayAttributes,
        stages: Array.isArray(entity.stages) ? entity.stages : [],
      }
      nodes.push(node)
      registerNodeKeys(node, [entityName, ...(Array.isArray(entity.aliases) ? entity.aliases : [])])
    }

    evolutionSnapshots.forEach((snapshot, key) => {
      if (!nodeByKey.has(key)) {
        ensureReferenceNode(snapshot.name, {
          label: '推演实体',
          summary: snapshot.stateChanges || snapshot.newStatus || '推演结果中出现的实体。',
        })
      }
    })

    const pushEdge = (sourceNode, targetNode, relationship = {}) => {
      if (!sourceNode || !targetNode) {
        return
      }
      const relationName = String(relationship.type || relationship.name || '关联').trim() || '关联'
      const fact = String(relationship.description || relationship.source_event || relationship.fact || '').trim()
      const edgeKey = [sourceNode.uuid, targetNode.uuid, relationName, fact].join('|')
      if (edgeKeys.has(edgeKey)) {
        return
      }
      edgeKeys.add(edgeKey)
      edges.push({
        uuid: relationship.id || `rel-${edges.length}`,
        name: relationName,
        fact,
        source_node_uuid: sourceNode.uuid,
        target_node_uuid: targetNode.uuid,
        attributes: relationship,
      })
    }

    for (const entity of w.entities || []) {
      const sourceNode = ensureReferenceNode(entity?.name, { label: entity?.type || 'Entity' })
      for (const relationship of Array.isArray(entity?.relationships) ? entity.relationships : []) {
        const targetName = String(relationship?.target || '').trim()
        if (!targetName) {
          continue
        }
        const targetNode = ensureReferenceNode(targetName, {
          label: '引用实体',
          summary: '在实体关系中被引用。',
        })
        pushEdge(sourceNode, targetNode, relationship)
      }
    }

    graphData.value = { graph_id: worldId.value, nodes, edges, node_count: nodes.length, edge_count: edges.length }
    if (!nodes.length) {
      graphMessage.value = '当前世界观暂无可显示的图谱节点。'
    }
  } catch (e) {
    graphData.value = null
    graphMessage.value = '图谱暂时不可用，但右侧推演结果仍可查看。'
  } finally {
    graphLoading.value = false
  }
}

function toggleGraphMax() {}

function applyEvolutionDetail(evo = {}) {
  status.value = evo.status || 'running'
  worldId.value = evo.world_id || worldId.value || ''
  evolutionScenario.value = evo.scenario || evolutionScenario.value || ''
  evolutionConfig.value = evo.config || evolutionConfig.value || {}
  consolidationSummary.value = evo.consolidation || null
  rounds.value = Array.isArray(evo.rounds)
    ? evo.rounds
        .filter(round => Number(round?.round_number || 0) > 0)
        .sort((left, right) => Number(left.round_number || 0) - Number(right.round_number || 0))
    : []
  currentRound.value = rounds.value.length
  totalRounds.value = Number(evo.config?.rounds || totalRounds.value || 5)
  evoType.value = evo.evolution_type || evoType.value || 'forward'
  parentEvoId.value = evo.parent_evolution_id || parentEvoId.value || ''
  if (rounds.value.length) {
    const latestRound = rounds.value[rounds.value.length - 1]
    lastNarrative.value = String(latestRound?.narrative || '').slice(0, 200)
  }
}

async function fetchEvolution() {
  try {
    const res = await service.get(`/api/evolution/${evolutionId.value}`)
    const evo = res.evolution || res
    applyEvolutionDetail(evo)
    if (worldId.value) {
      await loadGraph()
    }
  } catch (e) { loadError.value = '加载失败: ' + (e.message || '') } finally { loading.value = false }
}

async function refreshEvolutionDetail({ forceGraph = false } = {}) {
  const previousRoundCount = rounds.value.length
  const previousStatus = status.value
  const res = await service.get(`/api/evolution/${evolutionId.value}`)
  const evo = res.evolution || res
  applyEvolutionDetail(evo)
  if (worldId.value && (forceGraph || previousRoundCount !== rounds.value.length || previousStatus !== status.value || !graphData.value)) {
    await loadGraph()
  }
}

async function refreshEvolutionStatus() {
  const res = await service.get(`/api/evolution/${evolutionId.value}/status`)
  status.value = res.status || status.value || 'running'
  currentRound.value = Number(res.current_round ?? currentRound.value ?? 0)
  totalRounds.value = Number(res.total_rounds || totalRounds.value || 5)
  lastNarrative.value = res.last_narrative || lastNarrative.value || ''
  latestWarnings.value = Array.isArray(res.latest_warnings) ? res.latest_warnings : []
  warningCount.value = Number(res.warning_count || 0)
  if (res.error) {
    loadError.value = res.error
  }
  if (terminalStatuses.has(status.value)) {
    await refreshEvolutionDetail({ forceGraph: true })
  } else if (currentRound.value !== rounds.value.length) {
    await refreshEvolutionDetail()
  }
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

function startPolling() {
  if (pollTimer) {
    return
  }
  pollTimer = setInterval(async () => {
    try {
      await refreshEvolutionStatus()
      if (terminalStatuses.has(status.value)) {
        stopPolling()
      }
    } catch (e) {
      try {
        await refreshEvolutionDetail()
        if (terminalStatuses.has(status.value)) {
          stopPolling()
        }
      } catch (_) { /* ignore transient polling errors */ }
    }
  }, 2000)
}

onMounted(async () => {
  await fetchEvolution()
  if (!terminalStatuses.has(status.value)) {
    startPolling()
    refreshEvolutionStatus().catch(() => {})
  }
})
onUnmounted(stopPolling)

function startBranchFrom(roundNum) {
  router.push({ name: 'SimulationSetup', query: { worldId: worldId.value, parentEvolutionId: evolutionId.value, parentRound: roundNum, evolutionType: 'branch' } })
}

const forwardScenario = ref('')
const forwardRounds = ref(3)
const forwarding = ref(false)
async function startForward() {
  if (!forwardScenario.value.trim() || forwarding.value) return
  forwarding.value = true
  try {
    const lastRound = rounds.value[rounds.value.length - 1]
    const lastYear = lastRound?.year_advanced_to || lastRound?.raw_response?.year_advanced_to || ''
    const config = {
      rounds: forwardRounds.value,
      temperature: evolutionConfig.value?.temperature ?? 0.7,
      focus_areas: Array.isArray(evolutionConfig.value?.focus_areas) ? evolutionConfig.value.focus_areas : [],
    }
    if (lastYear) {
      config.time_span_start = lastYear
    }
    const response = await service.post(`/api/evolution/${evolutionId.value}/continue`, {
      scenario: forwardScenario.value,
      config,
    })
    totalRounds.value = Number(response.total_rounds || (rounds.value.length + Number(forwardRounds.value || 0)) || totalRounds.value)
    status.value = 'running'
    consolidationSummary.value = null
    forwardScenario.value = ''
    startPolling()
    await refreshEvolutionDetail({ forceGraph: true })
  } catch (e) {
    alert('继续推演失败: ' + (e.message || ''))
  } finally {
    forwarding.value = false
  }
}

const selectedEntities = ref([])
const selectedEvents = ref([])
const applying = ref(false)
const applyMsg = ref('')
const applyErr = ref('')

async function applyChanges() {
  applying.value = true; applyMsg.value = ''; applyErr.value = ''
  try {
    const res = await service.post(`/api/evolution/${evolutionId.value}/apply`, {
      entities: selectedEntities.value.map(e => ({ round: e.round, name: e.name, state_changes: e.state_changes, new_status: e.new_status })),
      events: selectedEvents.value,
      rounds: [...new Set(selectedEntities.value.map(e => e.round))],
    })
    applyMsg.value = res.message || '应用成功'
    selectedEntities.value = []
    selectedEvents.value = []
  } catch (e) { applyErr.value = '应用失败: ' + (e.message || '') } finally { applying.value = false }
}

// Entity chat
const chatEntity = ref(null)
const chatMessages = ref([])
const chatInput = ref('')
const chatLoading = ref(false)
const chatProfileLoading = ref(false)
const chatBrief = ref('')
const chatCurrentTime = ref('')
const chatCurrentStatus = ref('')
const chatProfileNotice = ref('')
const chatProfileCollapsed = ref(false)

function getCurrentEvolutionTime() {
  const latestRound = [...(rounds.value || [])]
    .filter(round => Number(round?.round_number || 0) > 0)
    .sort((left, right) => Number(right?.round_number || 0) - Number(left?.round_number || 0))[0]

  if (latestRound?.year_advanced_to) {
    return latestRound.year_advanced_to
  }

  const timeline = consolidationSummary.value?.timeline || []
  const latestTimelineItem = [...timeline].reverse().find(item => item?.time)
  if (latestTimelineItem?.time) {
    return latestTimelineItem.time
  }

  const anchor = evolutionConfig.value?.resolved_anchor || {}
  return anchor.start_time || evolutionConfig.value?.time_span_start || ''
}

function buildLocalEntityBrief(entityName, sourceEntity = null) {
  const normalizedName = normalizeGraphKey(entityName)
  if (!normalizedName) {
    return null
  }

  const graphNode = sourceEntity?.name
    ? sourceEntity
    : (graphData.value?.nodes || []).find(node => normalizeGraphKey(node?.name) === normalizedName)

  const finalState = (consolidationSummary.value?.final_entity_states || []).find(item => normalizeGraphKey(item?.name) === normalizedName)

  let latestChange = null
  for (const round of [...(rounds.value || [])].sort((left, right) => Number(right?.round_number || 0) - Number(left?.round_number || 0))) {
    const matched = (round.affected_entities || []).find(item => normalizeGraphKey(item?.name) === normalizedName)
    if (matched) {
      latestChange = {
        roundNumber: round.round_number,
        yearAdvancedTo: round.year_advanced_to,
        newStatus: matched.new_status || '',
        stateChanges: matched.state_changes || '',
      }
      break
    }
  }

  const attrs = graphNode?.attributes || {}
  const currentTime = latestChange?.yearAdvancedTo || getCurrentEvolutionTime()
  const currentStatus = finalState?.final_status
    || latestChange?.newStatus
    || latestChange?.stateChanges
    || attrs['推演最新状态']
    || attrs['当前状态']
    || ''

  const detailLines = Object.entries(attrs)
    .filter(([key, value]) => value && !['推演轮次', '推演最新状态', '推演变化'].includes(key))
    .slice(0, 8)
    .map(([key, value]) => `- ${key}: ${String(value)}`)

  const lines = [
    `姓名: ${graphNode?.name || finalState?.name || entityName}`,
  ]

  const typeLabel = graphNode?.labels?.find(label => label && label !== 'Entity') || graphNode?.labels?.[0] || ''
  if (typeLabel) {
    lines.push(`类型: ${typeLabel}`)
  }
  if (currentTime || currentStatus) {
    lines.push('当前角色锚点（最高优先级）:')
    if (currentTime) {
      lines.push(`- 当前时间: ${currentTime}`)
    }
    if (currentStatus) {
      lines.push(`- 当前身份/状态: ${currentStatus}`)
    }
  }
  if (latestChange || finalState) {
    lines.push('本次推演中的角色演化:')
    if (latestChange) {
      const roundHeader = latestChange.yearAdvancedTo
        ? `- 第${latestChange.roundNumber}轮（${latestChange.yearAdvancedTo}）`
        : `- 第${latestChange.roundNumber}轮`
      const changeText = latestChange.newStatus || latestChange.stateChanges
      lines.push(changeText ? `${roundHeader}: ${changeText}` : roundHeader)
    }
    if (finalState?.final_status) {
      lines.push(`- 推演结局: ${finalState.final_status}`)
    }
  }

  const baseIntro = attrs['简介'] || graphNode?.summary || ''
  if (baseIntro) {
    lines.push('原始设定/图谱摘要（前端兜底生成）:')
    lines.push(String(baseIntro))
  }
  if (detailLines.length) {
    lines.push('补充资料:')
    lines.push(...detailLines)
  }

  const brief = lines.filter(Boolean).join('\n')
  if (!brief.trim()) {
    return null
  }

  return {
    character_brief: brief,
    current_time: currentTime,
    current_status: currentStatus,
  }
}

async function fetchEntityProfile(entityName) {
  if (!worldId.value || !entityName) return
  const fallbackProfile = buildLocalEntityBrief(entityName, chatEntity.value)
  if (fallbackProfile) {
    chatBrief.value = fallbackProfile.character_brief || ''
    chatCurrentTime.value = fallbackProfile.current_time || ''
    chatCurrentStatus.value = fallbackProfile.current_status || ''
    chatProfileNotice.value = '当前先使用页面里的推演数据生成角色小传，稍后会尝试补全。'
  }
  chatProfileLoading.value = true
  try {
    const res = await service.post('/api/evolution/entity-chat', {
      world_id: worldId.value,
      evolution_id: evolutionId.value,
      entity_name: entityName,
      question: '',
      history: [],
    })
    chatBrief.value = res.character_brief || ''
    chatCurrentTime.value = res.current_time || ''
    chatCurrentStatus.value = res.current_status || ''
    chatProfileNotice.value = ''
    if (res.entity_name && chatEntity.value) {
      chatEntity.value = { ...chatEntity.value, name: res.entity_name }
    }
  } catch (e) {
    if (fallbackProfile) {
      chatProfileNotice.value = `后端角色小传补全失败，当前显示的是基于本页推演数据生成的版本。${e?.message ? ` 原因: ${e.message}` : ''}`
    } else {
      chatBrief.value = `角色小传生成失败${e?.message ? `: ${e.message}` : '，请稍后重试。'}`
      chatCurrentTime.value = ''
      chatCurrentStatus.value = ''
      chatProfileNotice.value = ''
    }
  } finally {
    chatProfileLoading.value = false
  }
}

function resetChatState(entity) {
  if (typeof entity === 'string') {
    chatEntity.value = { name: entity }
  } else {
    chatEntity.value = entity ? { ...entity } : null
  }
  chatMessages.value = []
  chatInput.value = ''
  chatBrief.value = ''
  chatCurrentTime.value = ''
  chatCurrentStatus.value = ''
  chatProfileNotice.value = ''
}

async function openEvolutionEntityChat(entity) {
  const entityName = typeof entity === 'string' ? entity : entity?.name || ''
  if (!entityName) {
    return
  }
  resetChatState(entity)
  await fetchEntityProfile(entityName)
}

async function onEntityClick(entityData) {
  const entityName = entityData?.name || ''
  if (!entityName) {
    return
  }
  resetChatState(entityData)
  await fetchEntityProfile(entityName)
}

async function sendChat() {
  if (!chatInput.value.trim() || chatLoading.value) return
  chatLoading.value = true
  const userMsg = chatInput.value
  chatMessages.value.push({ role: 'user', content: userMsg })
  chatInput.value = ''
  try {
    const res = await service.post('/api/evolution/entity-chat', {
      world_id: worldId.value,
      evolution_id: evolutionId.value,
      entity_name: chatEntity.value.name,
      question: userMsg,
      history: chatMessages.value.slice(0, -1),
    })
    chatMessages.value.push({ role: 'assistant', content: res.reply || '...' })
    chatBrief.value = res.character_brief || chatBrief.value
    chatCurrentTime.value = res.current_time || chatCurrentTime.value
    chatCurrentStatus.value = res.current_status || chatCurrentStatus.value
    if (res.entity_name) {
      chatEntity.value = { ...chatEntity.value, name: res.entity_name }
    }
  } catch (e) {
    chatMessages.value.push({ role: 'assistant', content: '对话失败: ' + (e.message || '') })
  } finally {
    chatLoading.value = false
  }
}
</script>

<style scoped>
.evo-page { height: calc(100vh - 56px); display: flex; flex-direction: column; background: var(--wf-bg-primary); }
.evo-header { display: flex; justify-content: space-between; align-items: center; padding: var(--spacing-md) var(--spacing-lg); border-bottom: 1px solid rgba(255, 255, 255, 0.06); }
.evo-header-right { display: flex; gap: var(--spacing-sm); align-items: center; }

.state-box { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: var(--spacing-md); padding: var(--spacing-2xl); flex: 1; }
.evo-layout { display: flex; flex: 1; overflow: hidden; }
.evo-graph-panel { width: 50%; border-right: 1px solid rgba(255, 255, 255, 0.06); overflow-y: auto; background: var(--wf-bg-primary); }
.evo-graph-panel :deep(.graph-panel) { height: 100%; }
.evo-graph-panel :deep(.graph-container) { height: calc(100% - 44px); }
.graph-placeholder { display: flex; align-items: center; justify-content: center; height: 100%; color: var(--wf-text-muted); }

.evo-right { flex: 1; display: flex; flex-direction: column; overflow-y: auto; overflow-x: hidden; min-height: 0; }

.evo-meta { margin: var(--spacing-md); margin-bottom: 0; }
.evo-meta-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--spacing-sm); }
.meta-block { padding: var(--spacing-sm); border-radius: var(--radius-sm); background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.05); }
.meta-block.is-wide { grid-column: 1 / -1; }
.meta-label { display: block; font-size: 0.78rem; color: var(--wf-text-muted); margin-bottom: 4px; }
.meta-value { margin: 0; font-size: 0.88rem; line-height: 1.6; color: var(--wf-text-primary); white-space: pre-wrap; }

.inline-status { margin: var(--spacing-md); margin-bottom: 0; display: flex; align-items: center; gap: var(--spacing-md); }
.inline-status-main { flex: 1; min-width: 0; }
.inline-status h4 { margin: 0 0 4px; font-size: 0.95rem; color: var(--wf-text-primary); }
.inline-status p { margin: 0; font-size: 0.84rem; color: var(--wf-text-secondary); }
.inline-progress-meta { display: flex; justify-content: space-between; gap: var(--spacing-md); margin: var(--spacing-sm) 0 6px; font-size: 0.78rem; color: var(--wf-text-muted); }
.progress-bar.compact { height: 6px; }
.last-narrative { margin-top: var(--spacing-sm) !important; color: var(--wf-text-primary) !important; }

.result-summary { margin: var(--spacing-md); margin-bottom: 0; display: flex; flex-direction: column; gap: var(--spacing-sm); }
.result-summary-header { display: flex; align-items: center; justify-content: space-between; gap: var(--spacing-sm); }
.result-summary-header h3 { margin: 0; font-size: 1rem; color: var(--wf-text-primary); }
.result-summary-text { margin: 0; line-height: 1.8; color: var(--wf-text-primary); white-space: pre-wrap; }
.result-chip-list { display: flex; flex-wrap: wrap; gap: var(--spacing-xs); }
.result-section { display: flex; flex-direction: column; gap: var(--spacing-xs); }
.result-section h4 { margin: 0; font-size: 0.88rem; color: var(--wf-text-secondary); }
.result-list { margin: 0; padding-left: 1.1rem; color: var(--wf-text-primary); }
.result-timeline { display: flex; flex-direction: column; gap: 6px; }
.final-state-list { display: flex; flex-direction: column; gap: var(--spacing-sm); }
.final-state-card { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--spacing-sm); padding: var(--spacing-sm); border-radius: var(--radius-sm); background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.05); }
.final-state-main h5 { margin: 0 0 4px; font-size: 0.9rem; color: var(--wf-text-primary); }
.final-state-main p { margin: 0; font-size: 0.84rem; line-height: 1.6; color: var(--wf-text-secondary); }
.timeline-item { display: grid; grid-template-columns: 110px 1fr; gap: var(--spacing-sm); align-items: start; }
.timeline-time { font-size: 0.78rem; color: var(--wf-accent); }
.timeline-event { font-size: 0.86rem; color: var(--wf-text-primary); line-height: 1.5; }

.progress-section { background: rgba(255, 255, 255, 0.03); border-bottom: 1px solid rgba(255, 255, 255, 0.06); padding: var(--spacing-sm) var(--spacing-lg); }
.progress-info { display: flex; justify-content: space-between; font-size: 0.85rem; color: var(--wf-text-secondary); margin-bottom: 4px; }
.progress-pct { font-weight: 600; color: var(--wf-accent); }
.progress-bar { height: 3px; background: rgba(255, 255, 255, 0.06); border-radius: 2px; overflow: hidden; }
.progress-fill { height: 100%; background: var(--wf-accent); transition: width 0.5s ease; box-shadow: 0 0 8px var(--wf-accent-glow); }

.rounds-scroll { flex: 0 0 auto; min-height: 0; overflow: visible; padding: var(--spacing-md); display: flex; flex-direction: column; gap: var(--spacing-md); }

.round-card { }
.round-header { display: flex; justify-content: space-between; margin-bottom: var(--spacing-sm); }
.round-badge { font-family: var(--font-mono); font-size: 0.85rem; font-weight: 600; color: var(--wf-accent); }
.round-year { font-size: 0.8rem; color: var(--wf-text-muted); }
.round-narrative { font-size: 0.9rem; line-height: 1.7; color: var(--wf-text-primary); white-space: pre-wrap; margin-bottom: var(--spacing-sm); }

.round-entities h4, .round-events h4 { font-size: 0.8rem; color: var(--wf-text-secondary); margin-bottom: 4px; }
.entity-change { padding: var(--spacing-sm); background: rgba(255, 255, 255, 0.04); border-radius: var(--radius-sm); margin-bottom: 4px; display: flex; align-items: baseline; gap: var(--spacing-sm); }
.ent-name { font-weight: 600; }
.mini-event { display: flex; gap: var(--spacing-sm); padding: 2px 0; font-size: 0.85rem; }
.evt-name { color: var(--wf-text-primary); }
.evt-date { color: var(--wf-accent); font-size: 0.8rem; }

.round-actions { margin-top: var(--spacing-sm); }
.btn-xs { padding: 4px 10px; font-size: 0.75rem; border-radius: var(--radius-full); }

.forward-section { }
.forward-section h4 { font-size: 0.9rem; color: var(--wf-text-primary); margin-bottom: 4px; }
.scenario-input { width: 100%; background: var(--wf-bg-input); border: 1px solid var(--wf-border); border-radius: var(--radius-md); color: var(--wf-text-primary); padding: var(--spacing-sm); resize: vertical; font-size: 0.85rem; }
.scenario-input:focus { outline: none; border-color: var(--wf-accent); }
.forward-params { display: flex; align-items: center; gap: var(--spacing-md); margin-top: var(--spacing-sm); }
.forward-params label { font-size: 0.85rem; color: var(--wf-text-secondary); }
.forward-params input { width: 60px; }

/* Apply Dialog */
.apply-dialog { max-width: 620px; max-height: 70vh; }
.dialog-body { overflow-y: auto; }
.hint { font-size: 0.8rem; color: var(--wf-text-muted); margin-bottom: var(--spacing-sm); }
.apply-list { max-height: 400px; overflow-y: auto; }
.apply-round-group { margin-bottom: var(--spacing-sm); }
.apply-round-group h5 { font-size: 0.8rem; color: var(--wf-text-muted); margin-bottom: 4px; }
.apply-checkbox { display: flex; align-items: flex-start; gap: var(--spacing-sm); padding: 4px 0; font-size: 0.85rem; cursor: pointer; }
.apply-ent-name { font-weight: 500; color: var(--wf-text-primary); min-width: 120px; }
.apply-ent-change { color: var(--wf-text-secondary); font-size: 0.8rem; flex: 1; }

/* Chat Dialog */
.entity-chat-dialog { max-width: 560px; height: 520px; display: flex; flex-direction: column; min-height: 0; }
.chat-profile-card { padding: var(--spacing-sm) var(--spacing-md); background: rgba(255, 255, 255, 0.03); border-bottom: 1px solid var(--wf-border); display: flex; flex-direction: column; gap: var(--spacing-sm); flex: 0 0 auto; max-height: 210px; overflow-y: auto; }
.chat-profile-loading { font-size: 0.84rem; color: var(--wf-text-muted); }
.chat-profile-notice { font-size: 0.8rem; line-height: 1.6; color: var(--wf-accent); }
.chat-profile-meta { display: flex; flex-wrap: wrap; gap: var(--spacing-xs); }
.chat-profile-toggle-text { display: inline-flex; align-items: center; gap: 4px; font-size: 0.8rem; color: var(--wf-text-muted); }
.chat-profile-text { margin: 0; font-size: 0.85rem; line-height: 1.7; color: var(--wf-text-secondary); white-space: pre-wrap; }
.chat-messages { flex: 1; min-height: 0; overflow-y: auto; padding: var(--spacing-sm); display: flex; flex-direction: column; gap: var(--spacing-sm); }
.chat-msg { padding: var(--spacing-sm) var(--spacing-md); border-radius: var(--radius-md); font-size: 0.9rem; max-width: 85%; }
.chat-msg.user { background: var(--wf-accent-muted); color: var(--wf-accent); align-self: flex-end; border: 1px solid rgba(255, 255, 175, 0.12); }
.chat-msg.assistant { background: rgba(255, 255, 255, 0.04); color: var(--wf-text-secondary); align-self: flex-start; border: 1px solid var(--wf-border); }
.chat-input-row { display: flex; gap: var(--spacing-sm); padding: var(--spacing-sm); border-top: 1px solid var(--wf-border); }
.chat-input { flex: 1; }

.btn-sm { padding: 8px 20px; font-size: 13px; border-radius: var(--radius-full); }
</style>
