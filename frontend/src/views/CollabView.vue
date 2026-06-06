<template>
  <div class="collab-modal-overlay" @click.self="goBackToWorldBuilder">
    <div class="collab-modal">
      <!-- 弹窗头部 -->
      <div class="collab-modal-header">
        <div class="collab-modal-title">
          <h1>联机房间</h1>
          <span class="sync-badge" :class="syncBadgeClass">{{ syncStatus }}</span>
        </div>
        <div class="collab-modal-actions">
          <button class="btn btn-secondary btn-sm" :disabled="loading" @click="bootstrap" title="刷新">
            <SvgIcon name="refresh" :size="14" />
          </button>
          <button class="collab-close-btn" @click="goBackToWorldBuilder" title="关闭">
            <SvgIcon name="close" :size="16" />
          </button>
        </div>
      </div>

      <!-- 错误提示 -->
      <div v-if="error" class="alert error">{{ error }}</div>

      <!-- 局域网联机信息 -->
      <section class="lan-panel card">
        <div class="panel-head">
          <div>
            <h2>局域网联机</h2>
            <p>把下面的房间邀请链接发给同一局域网内的成员。若无法访问，请确认主机防火墙已放行前端与后端端口。</p>
          </div>
        </div>

        <div class="lan-grid">
          <div class="lan-card">
            <span>主机访问地址</span>
            <strong>{{ primaryFrontendUrl || '正在检测...' }}</strong>
            <small v-if="lanInfo?.backend_port">后端端口 {{ lanInfo.backend_port }}</small>
          </div>
          <div class="lan-card">
            <span>当前房间</span>
            <strong>{{ currentRoom?.name || '未选择房间' }}</strong>
            <small>{{ currentRoom?.id || '选择或创建房间后生成邀请链接' }}</small>
          </div>
        </div>

        <div v-if="roomInviteUrl" class="invite-row">
          <input class="invite-input" :value="roomInviteUrl" readonly>
          <button class="btn btn-primary" type="button" @click="copyInviteLink">复制邀请链接</button>
        </div>
        <div v-if="copyFeedback" class="copy-feedback">{{ copyFeedback }}</div>

        <div v-if="lanAddresses.length" class="lan-address-list">
          <span v-for="address in lanAddresses" :key="address.host" class="lan-address-chip">
            {{ address.frontend_url }}
          </span>
        </div>
      </section>

      <!-- 主体内容区 -->
      <section class="collab-layout">
        <!-- 左侧：房间列表 -->
        <aside class="room-panel card">
          <div class="panel-head">
            <h2>房间</h2>
            <span>{{ rooms.length }} 个</span>
          </div>
          <form class="create-room" @submit.prevent="createRoom">
            <input v-model="newRoomName" placeholder="新房间名称" />
            <button class="btn btn-primary" :disabled="!newRoomName.trim()">创建</button>
          </form>
          <form class="create-room" @submit.prevent="joinRoomById">
            <input v-model="joinRoomId" placeholder="输入房间 ID 加入" />
            <button class="btn btn-secondary" :disabled="!joinRoomId.trim()">加入</button>
          </form>
          <div class="room-list">
            <button
              v-for="room in rooms"
              :key="room.id"
              class="room-item"
              :class="{ active: currentRoom?.id === room.id }"
              @click="selectRoom(room)"
            >
              <strong>{{ room.name }}</strong>
              <small>{{ room.description || room.id }}</small>
            </button>
          </div>
        </aside>

        <!-- 中间：事件与消息 -->
        <main class="event-panel card">
          <div class="panel-head">
            <div>
              <h2>{{ currentRoom?.name || '未选择房间' }}</h2>
              <p v-if="currentRoom">{{ currentRoom.description || '暂无房间说明' }}</p>
            </div>
            <span class="sync-state">seq {{ latestSeq }}</span>
          </div>

          <div ref="eventsScroll" class="events">
            <div v-if="events.length === 0" class="empty">暂无事件，发送一条消息开始同步。</div>
            <article v-for="event in events" :key="event.id" class="event-item" :class="event.type">
              <span class="event-type">{{ eventTypeLabel(event.type) }}</span>
              <div class="event-body">
                <div class="event-meta">
                  <strong>{{ event.actor_id }}</strong>
                  <time>{{ formatTime(event.created_at) }}</time>
                </div>
                <p>{{ eventText(event) }}</p>
              </div>
            </article>
          </div>

          <form class="message-box" @submit.prevent="sendMessage">
            <input v-model="messageText" :disabled="!currentRoom" placeholder="向房间发送消息..." />
            <button class="btn btn-primary" :disabled="!currentRoom || !messageText.trim()">
              <SvgIcon name="send" :size="14" />
              <span>发送</span>
            </button>
          </form>
        </main>

        <!-- 右侧：成员列表 -->
        <aside class="member-panel card">
          <div class="panel-head">
            <h2>成员</h2>
            <span>{{ members.length }} 人</span>
          </div>
          <form class="identity-card" @submit.prevent="saveDisplayName">
            <span>当前用户</span>
            <input v-model="displayNameDraft" placeholder="你的局域网昵称" />
            <small>{{ identity.userId }}</small>
            <button class="btn btn-secondary" type="submit" :disabled="!displayNameDraft.trim()">保存昵称</button>
          </form>
          <div class="member-list">
            <div v-for="member in members" :key="member.user_id" class="member-item">
              <span class="dot" :class="{ online: member.online }"></span>
              <div class="member-info">
                <strong>{{ member.display_name }}</strong>
                <small>{{ member.role }} · {{ member.online ? '在线' : '离线' }}</small>
              </div>
            </div>
          </div>
        </aside>
      </section>
    </div>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, computed, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { collabApi } from '../api/collab'
import SvgIcon from '../components/ui/SvgIcon.vue'
import { ensureCollabIdentity, writeCollabDisplayName } from '../utils/collabIdentity.js'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const error = ref('')
const identity = ref(ensureCollabIdentity())
const displayNameDraft = ref(identity.value.displayName)
const workspace = ref(null)
const rooms = ref([])
const currentRoom = ref(null)
const members = ref([])
const events = ref([])
const latestSeq = ref(0)
const newRoomName = ref('')
const joinRoomId = ref(String(route.query.roomId || '').trim())
const messageText = ref('')
const lanInfo = ref(null)
const roomInvite = ref(null)
const copyFeedback = ref('')
const syncStatus = ref('未连接')
const primaryFrontendUrl = ref('')
const roomInviteUrl = ref('')
const lanAddresses = ref([])
const eventsScroll = ref(null)
let heartbeatTimer = null
let syncLoopToken = 0
let copyFeedbackTimer = null

const syncBadgeClass = computed(() => {
  if (syncStatus.value === '已连接') return 'sync-connected'
  if (syncStatus.value === '同步中' || syncStatus.value === '正在加入') return 'sync-syncing'
  if (syncStatus.value === '同步重试中') return 'sync-retry'
  return 'sync-disconnected'
})

function actorPayload() {
  return {
    user_id: identity.value.userId,
    display_name: identity.value.displayName,
  }
}

function applyLanInfo(lan) {
  lanInfo.value = lan || null
  primaryFrontendUrl.value = lan?.primary_frontend_url || ''
  lanAddresses.value = Array.isArray(lan?.addresses) ? lan.addresses : []
}

function applyRoomInvite(payload) {
  roomInvite.value = payload || null
  roomInviteUrl.value = payload?.invite_url || payload?.lan?.primary_join_url || ''
  if (payload?.lan) {
    applyLanInfo(payload.lan)
  }
}

function formatTime(value) {
  if (!value) return ''
  return new Date(value).toLocaleTimeString()
}

function eventText(event) {
  if (event.type === 'message') return event.payload?.content || ''
  if (event.type === 'member.joined') return '加入了房间'
  if (event.type === 'member.left') return '离开了房间'
  if (event.type === 'room.created') return '创建了房间'
  if (event.type === 'world.saved') return event.payload?.summary || '保存了世界观'
  return JSON.stringify(event.payload || {})
}

function eventTypeLabel(type) {
  const labels = {
    message: '消息',
    'member.joined': '加入',
    'member.left': '离开',
    'room.created': '创建房间',
    'world.saved': '保存世界观',
  }
  return labels[type] || type
}

function scrollEventsToBottom() {
  nextTick(() => {
    const el = eventsScroll.value
    if (el) {
      el.scrollTop = el.scrollHeight
    }
  })
}

function goBackToWorldBuilder() {
  const worldId = String(route.query.worldId || '').trim()
  if (worldId) {
    router.push({ name: 'WorldBuilder', query: { worldId } })
    return
  }
  router.push({ name: 'WorldBuilder' })
}

function mergeEvents(incoming = [], latest = 0) {
  const knownIds = new Set(events.value.map(event => event.id))
  const additions = incoming.filter(event => event?.id && !knownIds.has(event.id))
  const hasNew = additions.length > 0
  if (hasNew) {
    events.value.push(...additions)
  }
  latestSeq.value = Math.max(latestSeq.value, Number(latest || 0), ...incoming.map(event => Number(event.seq || 0)))
  if (hasNew) {
    scrollEventsToBottom()
  }
}

async function loadLanInfo() {
  try {
    const res = await collabApi.getLanInfo()
    applyLanInfo(res.lan)
  } catch (e) {
    // LAN 信息是辅助能力，不阻断房间功能。
  }
}

async function bootstrap() {
  loading.value = true
  error.value = ''
  try {
    await loadLanInfo()
    const res = await collabApi.bootstrap()
    workspace.value = res.workspace
    rooms.value = res.rooms || []
    const requestedRoomId = String(route.query.roomId || '').trim()
    let targetRoom = requestedRoomId
      ? rooms.value.find(room => room.id === requestedRoomId)
      : null
    if (requestedRoomId && !targetRoom) {
      const roomRes = await collabApi.getRoom(requestedRoomId)
      targetRoom = roomRes.room
      rooms.value = [targetRoom, ...rooms.value.filter(room => room.id !== targetRoom.id)]
    }
    targetRoom = targetRoom || res.room || rooms.value[0] || null
    if (targetRoom) await enterRoom(targetRoom)
  } catch (e) {
    error.value = e.message || '联机房间加载失败'
  } finally {
    loading.value = false
  }
}

async function loadRooms() {
  const res = await collabApi.listRooms(workspace.value?.id || '')
  rooms.value = res.rooms || []
}

async function createRoom() {
  const name = newRoomName.value.trim()
  if (!name) return
  const res = await collabApi.createRoom({
    name,
    workspace_id: workspace.value?.id,
    ...actorPayload(),
  })
  newRoomName.value = ''
  await loadRooms()
  await enterRoom(res.room)
}

async function joinRoomById() {
  const roomId = joinRoomId.value.trim()
  if (!roomId) return
  try {
    const res = await collabApi.getRoom(roomId)
    const room = res.room
    rooms.value = [room, ...rooms.value.filter(item => item.id !== room.id)]
    await enterRoom(room)
  } catch (e) {
    error.value = e.message || '加入房间失败'
  }
}

async function selectRoom(room) {
  if (currentRoom.value?.id === room.id) return
  await enterRoom(room)
}

async function enterRoom(room) {
  syncLoopToken += 1
  currentRoom.value = room
  joinRoomId.value = room.id
  latestSeq.value = 0
  events.value = []
  syncStatus.value = '正在加入'
  await collabApi.joinRoom(room.id, actorPayload())
  await Promise.all([loadMembers(), pollEvents(), refreshRoomInvite()])
  syncStatus.value = '已连接'
  router.replace({
    name: 'Collab',
    query: {
      ...route.query,
      roomId: room.id,
    },
  })
  startSyncLoop(room.id)
}

async function refreshRoomInvite() {
  if (!currentRoom.value) {
    roomInvite.value = null
    roomInviteUrl.value = ''
    return
  }
  const res = await collabApi.getRoomInvite(currentRoom.value.id)
  applyRoomInvite(res)
}

async function loadMembers() {
  if (!currentRoom.value) return
  const res = await collabApi.listMembers(currentRoom.value.id)
  members.value = res.members || []
}

async function pollEvents() {
  if (!currentRoom.value) return
  const res = await collabApi.listEvents(currentRoom.value.id, latestSeq.value, 100)
  mergeEvents(res.events || [], res.latest_seq)
}

async function syncOnce(roomId) {
  const res = await collabApi.syncEvents(roomId, latestSeq.value, 100)
  mergeEvents(res.events || [], res.latest_seq)
}

function wait(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

function startSyncLoop(roomId) {
  const token = ++syncLoopToken
  const run = async () => {
    while (token === syncLoopToken && currentRoom.value?.id === roomId) {
      try {
        syncStatus.value = '同步中'
        await syncOnce(roomId)
        syncStatus.value = '已连接'
      } catch (e) {
        if (token !== syncLoopToken) return
        syncStatus.value = '同步重试中'
        await wait(1500)
      }
    }
  }
  run()
}

async function heartbeat() {
  if (!currentRoom.value) return
  await collabApi.heartbeat(currentRoom.value.id, { user_id: identity.value.userId })
  await loadMembers()
}

async function sendMessage() {
  const content = messageText.value.trim()
  if (!content || !currentRoom.value) return
  await collabApi.postMessage(currentRoom.value.id, content, { user_id: identity.value.userId })
  messageText.value = ''
  await pollEvents()
  scrollEventsToBottom()
}

async function copyInviteLink() {
  if (!roomInviteUrl.value) return
  try {
    await navigator.clipboard?.writeText(roomInviteUrl.value)
    copyFeedback.value = '邀请链接已复制'
  } catch (e) {
    copyFeedback.value = '复制失败，请手动复制链接'
  }
  if (copyFeedbackTimer) clearTimeout(copyFeedbackTimer)
  copyFeedbackTimer = setTimeout(() => {
    copyFeedback.value = ''
  }, 2500)
}

async function saveDisplayName() {
  identity.value = writeCollabDisplayName(displayNameDraft.value)
  displayNameDraft.value = identity.value.displayName
  if (currentRoom.value) {
    await collabApi.joinRoom(currentRoom.value.id, actorPayload())
    await loadMembers()
  }
}

onMounted(async () => {
  await bootstrap()
  heartbeatTimer = setInterval(() => heartbeat().catch(() => {}), 10000)
  scrollEventsToBottom()
})

onBeforeUnmount(() => {
  syncLoopToken += 1
  if (heartbeatTimer) clearInterval(heartbeatTimer)
  if (copyFeedbackTimer) clearTimeout(copyFeedbackTimer)
})
</script>

<style scoped>
/* ========== 弹窗遮罩层 ========== */
.collab-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.65);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: var(--spacing-lg);
  animation: overlayFadeIn 0.2s ease;
}

@keyframes overlayFadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

/* ========== 弹窗主体 ========== */
.collab-modal {
  background: var(--wf-bg-primary);
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-lg);
  width: 1280px;
  max-width: 95vw;
  max-height: 92vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.45);
  animation: modalSlideIn 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  overflow: hidden;
}

@keyframes modalSlideIn {
  from { opacity: 0; transform: translateY(16px) scale(0.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

/* ========== 弹窗头部 ========== */
.collab-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 1px solid var(--wf-border);
  background: rgba(255, 255, 255, 0.02);
  flex-shrink: 0;
}

.collab-modal-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.collab-modal-title h1 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--wf-text-primary);
}

.collab-modal-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.collab-close-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-md);
  border: 1px solid var(--wf-border);
  background: transparent;
  color: var(--wf-text-muted);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.collab-close-btn:hover {
  background: rgba(255, 82, 82, 0.12);
  border-color: rgba(255, 82, 82, 0.3);
  color: #ffb4b4;
}

/* 同步状态徽章 */
.sync-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  border-radius: var(--radius-full);
  font-size: 0.75rem;
  font-weight: 500;
  border: 1px solid transparent;
  transition: all 0.3s ease;
}

.sync-badge::before {
  content: '';
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.sync-connected {
  color: #8ee6a2;
  background: rgba(142, 230, 162, 0.10);
  border-color: rgba(142, 230, 162, 0.2);
}

.sync-syncing {
  color: var(--wf-accent);
  background: rgba(255, 255, 175, 0.08);
  border-color: rgba(255, 255, 175, 0.15);
  animation: pulseBadge 1.5s ease infinite;
}

.sync-retry {
  color: #f5a623;
  background: rgba(245, 166, 35, 0.10);
  border-color: rgba(245, 166, 35, 0.2);
}

.sync-disconnected {
  color: var(--wf-text-muted);
  background: rgba(255, 255, 255, 0.04);
  border-color: var(--wf-border);
}

@keyframes pulseBadge {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

/* ========== 局域网联机面板 ========== */
.lan-panel {
  margin: var(--spacing-md) var(--spacing-lg) 0;
  flex-shrink: 0;
}

.lan-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-md);
}

.lan-card {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px 14px;
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.035);
}

.lan-card span,
.lan-card small,
.copy-feedback,
.lan-address-chip {
  color: var(--wf-text-muted);
}

.lan-card strong {
  color: var(--wf-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.invite-row {
  display: flex;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-sm);
}

.invite-input {
  flex: 1;
  min-width: 0;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--wf-border);
  background: rgba(255, 255, 255, 0.04);
  color: var(--wf-text-primary);
}

.lan-address-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: var(--spacing-sm);
}

.lan-address-chip {
  padding: 4px 8px;
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-full);
  background: rgba(255, 255, 255, 0.035);
  font-size: 0.78rem;
}

/* ========== 主体三栏布局 ========== */
.collab-layout {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr) 240px;
  gap: var(--spacing-md);
  padding: var(--spacing-md) var(--spacing-lg) var(--spacing-lg);
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.card {
  padding: var(--spacing-md);
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.02);
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.panel-head {
  display: flex;
  justify-content: space-between;
  gap: var(--spacing-md);
  align-items: flex-start;
  margin-bottom: var(--spacing-md);
  flex-shrink: 0;
}

.panel-head h2 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
}

.panel-head p,
.panel-head span,
.identity-card span,
.identity-card small,
.member-item small {
  color: var(--wf-text-muted);
}

/* ========== 房间列表 ========== */
.room-panel {
  min-width: 0;
}

.create-room {
  display: flex;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-sm);
}

.create-room input {
  flex: 1;
  min-width: 0;
  padding: 8px 10px;
  border-radius: var(--radius-md);
  border: 1px solid var(--wf-border);
  background: rgba(255, 255, 255, 0.04);
  color: var(--wf-text-primary);
  font-size: 0.85rem;
}

.room-list {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

.room-item {
  display: block;
  width: 100%;
  text-align: left;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  border: 1px solid transparent;
  background: transparent;
  color: var(--wf-text-primary);
  cursor: pointer;
  margin-bottom: 6px;
  font-size: 0.9rem;
  transition: all var(--transition-fast);
}

.room-item small {
  display: block;
  margin-top: 3px;
  color: var(--wf-text-muted);
  font-size: 0.78rem;
}

.room-item.active,
.room-item:hover {
  background: rgba(255, 255, 255, 0.06);
  border-color: var(--wf-border-light);
}

.room-item.active {
  border-left: 3px solid var(--wf-accent);
}

/* ========== 事件面板 ========== */
.event-panel {
  min-width: 0;
}

.events {
  flex: 1;
  overflow-y: auto;
  padding-right: 4px;
  margin-bottom: var(--spacing-md);
  min-height: 0;
}

.empty {
  color: var(--wf-text-muted);
  text-align: center;
  padding: var(--spacing-2xl);
}

.event-item {
  display: flex;
  gap: var(--spacing-sm);
  padding: 10px 0;
  border-bottom: 1px solid var(--wf-border);
  animation: eventFadeIn 0.2s ease;
}

@keyframes eventFadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

.event-item:last-child {
  border-bottom: none;
}

.event-type {
  flex-shrink: 0;
  font-size: 11px;
  color: var(--wf-accent);
  font-family: var(--font-mono);
  width: 64px;
  padding-top: 2px;
}

.event-body {
  flex: 1;
  min-width: 0;
}

.event-meta {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: 3px;
}

.event-meta strong {
  font-size: 0.85rem;
  color: var(--wf-text-primary);
}

.event-meta time {
  font-size: 11px;
  color: var(--wf-text-muted);
}

.event-item p {
  margin: 0;
  color: var(--wf-text-secondary);
  font-size: 0.88rem;
  line-height: 1.5;
  word-break: break-word;
}

/* 事件类型颜色区分 */
.event-item.message .event-type { color: var(--wf-accent); }
.event-item.member\.joined .event-type { color: #8ee6a2; }
.event-item.member\.left .event-type { color: #ffb4b4; }
.event-item.room\.created .event-type { color: #a5b4fc; }
.event-item.world\.saved .event-type { color: #fcd34d; }

/* ========== 消息输入框 ========== */
.message-box {
  display: flex;
  gap: var(--spacing-sm);
  flex-shrink: 0;
}

.message-box input {
  flex: 1;
  min-width: 0;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--wf-border);
  background: rgba(255, 255, 255, 0.04);
  color: var(--wf-text-primary);
}

.message-box input:focus {
  outline: none;
  border-color: var(--wf-accent);
  box-shadow: 0 0 0 2px rgba(255, 255, 175, 0.08);
}

/* ========== 成员面板 ========== */
.member-panel {
  min-width: 0;
}

.identity-card {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
  padding: 10px 12px;
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.04);
  margin-bottom: var(--spacing-sm);
  flex-shrink: 0;
}

.identity-card input {
  padding: 8px 10px;
  border-radius: var(--radius-md);
  border: 1px solid var(--wf-border);
  background: rgba(255, 255, 255, 0.04);
  color: var(--wf-text-primary);
  font-size: 0.85rem;
}

.member-list {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

.member-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: 10px 12px;
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.04);
  margin-bottom: var(--spacing-xs);
  transition: background var(--transition-fast);
}

.member-item:hover {
  background: rgba(255, 255, 255, 0.06);
}

.member-info {
  flex: 1;
  min-width: 0;
}

.member-info strong {
  display: block;
  font-size: 0.88rem;
  color: var(--wf-text-primary);
}

.member-info small {
  font-size: 0.78rem;
  color: var(--wf-text-muted);
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--wf-text-muted);
  flex-shrink: 0;
}

.dot.online {
  background: #8ee6a2;
  box-shadow: 0 0 10px rgba(142, 230, 162, 0.5);
}

/* ========== 错误提示 ========== */
.alert.error {
  padding: 10px 14px;
  border-radius: var(--radius-md);
  color: #ffb4b4;
  background: rgba(255, 82, 82, 0.10);
  border: 1px solid rgba(255, 82, 82, 0.25);
  margin: var(--spacing-sm) var(--spacing-lg) 0;
  font-size: 0.88rem;
  flex-shrink: 0;
}

/* ========== 按钮小尺寸 ========== */
.btn-sm {
  padding: 6px 12px;
  font-size: 0.8rem;
}

/* ========== 响应式 ========== */
@media (max-width: 1024px) {
  .collab-layout {
    grid-template-columns: 220px minmax(0, 1fr) 200px;
  }
}

@media (max-width: 860px) {
  .collab-modal-overlay {
    padding: var(--spacing-sm);
  }

  .collab-modal {
    max-width: 100vw;
    max-height: 100vh;
    border-radius: var(--radius-md);
  }

  .collab-layout {
    grid-template-columns: 1fr;
    grid-template-rows: auto auto 1fr;
    overflow-y: auto;
  }

  .room-panel,
  .member-panel {
    max-height: 280px;
  }

  .lan-grid {
    grid-template-columns: 1fr;
  }

  .invite-row {
    flex-direction: column;
  }

  .invite-row .btn {
    width: 100%;
  }
}
</style>
