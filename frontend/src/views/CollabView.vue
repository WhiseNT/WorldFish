<template>
  <div class="collab-page">
    <header class="collab-hero">
      <div>
        <button class="back-link" type="button" @click="goBackToWorldBuilder">
          <SvgIcon name="chevron-left" :size="16" :stroke-width="2.2" />
          <span>返回世界观构建</span>
        </button>
        <h1>联机房间</h1>
        <p>在同一局域网内启动主机后，其他设备可通过邀请链接加入同一个房间，并通过成员心跳与事件日志实时同步。</p>
      </div>
      <button class="btn btn-secondary" :disabled="loading" @click="bootstrap">刷新</button>
    </header>

    <div v-if="error" class="alert error">{{ error }}</div>

    <section class="lan-panel card">
      <div class="panel-head">
        <div>
          <h2>局域网联机</h2>
          <p>把下面的房间邀请链接发给同一局域网内的成员。若无法访问，请确认主机防火墙已放行前端与后端端口。</p>
        </div>
        <span class="sync-state">{{ syncStatus }}</span>
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

    <section class="collab-layout">
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
      </aside>

      <main class="event-panel card">
        <div class="panel-head">
          <div>
            <h2>{{ currentRoom?.name || '未选择房间' }}</h2>
            <p v-if="currentRoom">{{ currentRoom.description || '暂无房间说明' }}</p>
          </div>
          <span class="sync-state">seq {{ latestSeq }}</span>
        </div>

        <div class="events">
          <div v-if="events.length === 0" class="empty">暂无事件，发送一条消息开始同步。</div>
          <article v-for="event in events" :key="event.id" class="event-item">
            <span class="event-type">{{ event.type }}</span>
            <div>
              <strong>{{ event.actor_id }}</strong>
              <p>{{ eventText(event) }}</p>
              <time>{{ formatTime(event.created_at) }}</time>
            </div>
          </article>
        </div>

        <form class="message-box" @submit.prevent="sendMessage">
          <input v-model="messageText" :disabled="!currentRoom" placeholder="向房间发送消息" />
          <button class="btn btn-primary" :disabled="!currentRoom || !messageText.trim()">发送</button>
        </form>
      </main>

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
        <div v-for="member in members" :key="member.user_id" class="member-item">
          <span class="dot" :class="{ online: member.online }"></span>
          <div>
            <strong>{{ member.display_name }}</strong>
            <small>{{ member.role }} · {{ member.online ? '在线' : '离线' }}</small>
          </div>
        </div>
      </aside>
    </section>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
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
let heartbeatTimer = null
let syncLoopToken = 0
let copyFeedbackTimer = null

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
  if (additions.length) {
    events.value.push(...additions)
  }
  latestSeq.value = Math.max(latestSeq.value, Number(latest || 0), ...incoming.map(event => Number(event.seq || 0)))
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
})

onBeforeUnmount(() => {
  syncLoopToken += 1
  if (heartbeatTimer) clearInterval(heartbeatTimer)
  if (copyFeedbackTimer) clearTimeout(copyFeedbackTimer)
})
</script>

<style scoped>
.collab-page {
  max-width: 1280px;
  margin: 0 auto;
  padding: var(--spacing-2xl) var(--spacing-lg);
}

.collab-hero {
  display: flex;
  justify-content: space-between;
  gap: var(--spacing-xl);
  align-items: flex-start;
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
  transition: color var(--transition-fast);
}

.back-link:hover {
  color: var(--wf-accent-hover);
}

.collab-hero h1 {
  margin-bottom: var(--spacing-sm);
  font-size: 2rem;
}

.collab-hero p {
  color: var(--wf-text-secondary);
  max-width: 760px;
  line-height: 1.7;
}

.lan-panel {
  margin-bottom: var(--spacing-lg);
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

.collab-layout {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr) 260px;
  gap: var(--spacing-lg);
}

.card {
  padding: var(--spacing-lg);
}

.panel-head {
  display: flex;
  justify-content: space-between;
  gap: var(--spacing-md);
  align-items: flex-start;
  margin-bottom: var(--spacing-md);
}

.panel-head h2 {
  margin: 0;
  font-size: 1.1rem;
}

.panel-head p,
.panel-head span,
.identity-card span,
.identity-card small,
.member-item small {
  color: var(--wf-text-muted);
}

.create-room,
.message-box,
.identity-card {
  display: flex;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-md);
}

.create-room input,
.message-box input,
.identity-card input {
  flex: 1;
  min-width: 0;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--wf-border);
  background: rgba(255, 255, 255, 0.04);
  color: var(--wf-text-primary);
}

.identity-card {
  flex-direction: column;
  padding: 12px;
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.04);
}

.room-item {
  display: block;
  width: 100%;
  text-align: left;
  padding: 12px;
  border-radius: var(--radius-md);
  border: 1px solid transparent;
  background: transparent;
  color: var(--wf-text-primary);
  cursor: pointer;
  margin-bottom: 8px;
}

.room-item small {
  display: block;
  margin-top: 4px;
  color: var(--wf-text-muted);
}

.room-item.active,
.room-item:hover {
  background: rgba(255, 255, 255, 0.06);
  border-color: var(--wf-border-light);
}

.events {
  min-height: 420px;
  max-height: 560px;
  overflow-y: auto;
  padding-right: 4px;
  margin-bottom: var(--spacing-md);
}

.empty {
  color: var(--wf-text-muted);
  text-align: center;
  padding: var(--spacing-2xl);
}

.event-item {
  display: flex;
  gap: var(--spacing-md);
  padding: 12px 0;
  border-bottom: 1px solid var(--wf-border);
}

.event-type {
  flex-shrink: 0;
  font-size: 12px;
  color: var(--wf-accent);
  font-family: var(--font-mono);
  width: 96px;
}

.event-item p {
  margin: 4px 0;
  color: var(--wf-text-secondary);
}

.event-item time {
  color: var(--wf-text-muted);
  font-size: 12px;
}

.member-item {
  padding: 12px;
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.04);
  margin-bottom: var(--spacing-sm);
}

.member-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--wf-text-muted);
}

.dot.online {
  background: #8ee6a2;
  box-shadow: 0 0 10px rgba(142, 230, 162, 0.5);
}

.alert.error {
  padding: 12px 14px;
  border-radius: var(--radius-md);
  color: #ffb4b4;
  background: rgba(255, 82, 82, 0.10);
  border: 1px solid rgba(255, 82, 82, 0.25);
  margin-bottom: var(--spacing-md);
}

@media (max-width: 980px) {
  .collab-layout,
  .lan-grid {
    grid-template-columns: 1fr;
  }

  .collab-hero,
  .invite-row {
    flex-direction: column;
  }

  .invite-row .btn {
    width: 100%;
  }
}
</style>
