<template>
  <div class="collab-page">
    <header class="collab-hero">
      <div>
        <button class="back-link" type="button" @click="goBackToWorldBuilder">
          <SvgIcon name="chevron-left" :size="16" :stroke-width="2.2" />
          <span>返回世界观构建</span>
        </button>
        <h1>联机房间</h1>
        <p>单人使用会进入默认本地房间；多人联机、跑团和协作编辑都会基于这里的房间、成员与事件日志扩展。</p>
      </div>
      <button class="btn btn-secondary" :disabled="loading" @click="bootstrap">刷新</button>
    </header>

    <div v-if="error" class="alert error">{{ error }}</div>

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
        <div class="user-card" v-if="user">
          <span>当前用户</span>
          <strong>{{ user.name }}</strong>
          <small>{{ user.id }}</small>
        </div>
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

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const error = ref('')
const user = ref(null)
const workspace = ref(null)
const rooms = ref([])
const currentRoom = ref(null)
const members = ref([])
const events = ref([])
const latestSeq = ref(0)
const newRoomName = ref('')
const messageText = ref('')
let pollTimer = null
let heartbeatTimer = null

function formatTime(value) {
  if (!value) return ''
  return new Date(value).toLocaleTimeString()
}

function eventText(event) {
  if (event.type === 'message') return event.payload?.content || ''
  if (event.type === 'member.joined') return '加入了房间'
  if (event.type === 'member.left') return '离开了房间'
  if (event.type === 'room.created') return '创建了房间'
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

async function bootstrap() {
  loading.value = true
  error.value = ''
  try {
    const res = await collabApi.bootstrap()
    user.value = res.user
    workspace.value = res.workspace
    rooms.value = res.rooms || []
    currentRoom.value = res.room || rooms.value[0] || null
    if (currentRoom.value) await enterRoom(currentRoom.value)
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
  const res = await collabApi.createRoom({ name, workspace_id: workspace.value?.id, user_id: user.value?.id })
  newRoomName.value = ''
  await loadRooms()
  await enterRoom(res.room)
}

async function selectRoom(room) {
  if (currentRoom.value?.id === room.id) return
  await enterRoom(room)
}

async function enterRoom(room) {
  currentRoom.value = room
  latestSeq.value = 0
  events.value = []
  await collabApi.joinRoom(room.id, { user_id: user.value?.id, display_name: user.value?.name })
  await Promise.all([loadMembers(), pollEvents()])
}

async function loadMembers() {
  if (!currentRoom.value) return
  const res = await collabApi.listMembers(currentRoom.value.id)
  members.value = res.members || []
}

async function pollEvents() {
  if (!currentRoom.value) return
  const res = await collabApi.listEvents(currentRoom.value.id, latestSeq.value, 100)
  const incoming = res.events || []
  if (incoming.length) {
    events.value.push(...incoming)
  }
  latestSeq.value = res.latest_seq || latestSeq.value
}

async function heartbeat() {
  if (!currentRoom.value) return
  await collabApi.heartbeat(currentRoom.value.id, { user_id: user.value?.id })
  await loadMembers()
}

async function sendMessage() {
  const content = messageText.value.trim()
  if (!content || !currentRoom.value) return
  await collabApi.postMessage(currentRoom.value.id, content, { user_id: user.value?.id })
  messageText.value = ''
  await pollEvents()
}

onMounted(async () => {
  await bootstrap()
  pollTimer = setInterval(() => pollEvents().catch(() => {}), 2500)
  heartbeatTimer = setInterval(() => heartbeat().catch(() => {}), 10000)
})

onBeforeUnmount(() => {
  if (pollTimer) clearInterval(pollTimer)
  if (heartbeatTimer) clearInterval(heartbeatTimer)
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
.user-card span,
.user-card small,
.member-item small {
  color: var(--wf-text-muted);
}

.create-room,
.message-box {
  display: flex;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-md);
}

.create-room input,
.message-box input {
  flex: 1;
  min-width: 0;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--wf-border);
  background: rgba(255, 255, 255, 0.04);
  color: var(--wf-text-primary);
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

.user-card,
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
  .collab-layout {
    grid-template-columns: 1fr;
  }
}
</style>
