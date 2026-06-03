<template>
  <div class="trpg-page">
    <header class="trpg-hero">
      <div>
        <button class="back-link" type="button" @click="router.push('/')">
          <SvgIcon name="chevron-left" :size="16" :stroke-width="2.2" />
          <span>返回首页</span>
        </button>
        <h1>TRPG 跑团</h1>
        <p>选择世界观并创建局域网跑团房间，成员可以同步聊天、掷骰、角色卡和场景记录。</p>
      </div>
      <button class="btn btn-secondary" :disabled="loading" @click="bootstrap">刷新</button>
    </header>

    <div v-if="error" class="alert error">{{ error }}</div>

    <section class="trpg-layout">
      <aside class="trpg-sidebar card">
        <div class="panel-head">
          <h2>开团设置</h2>
          <span>{{ syncStatus }}</span>
        </div>

        <label class="field-block">
          世界观
          <select v-model="selectedWorldId" :disabled="Boolean(currentRoom)">
            <option value="">选择世界观</option>
            <option v-for="world in worlds" :key="world.id" :value="world.id">
              {{ world.name || '未命名世界观' }}
            </option>
          </select>
        </label>

        <label class="field-block">
          跑团类型
          <select v-model="systemType" :disabled="Boolean(currentRoom)">
            <option value="dnd">DND 战术团</option>
            <option value="coc">COC 调查团</option>
          </select>
        </label>

        <label class="field-block">
          使用地图
          <select v-model="activeMapId" :disabled="!worldMaps.length" @change="handleActiveMapChange">
            <option value="">选择世界观地图</option>
            <option v-for="map in recommendedMaps" :key="map.id" :value="map.id">
              {{ map.name }} · {{ map.type }}
            </option>
          </select>
        </label>
        <router-link
          v-if="selectedWorldId"
          class="map-maintain-link"
          :to="{ name: 'WorldBuilder', query: { worldId: selectedWorldId, tab: 'map' } }"
        >
          去世界观地图界面维护地图
        </router-link>
        <p v-if="selectedWorldId && !worldMaps.length" class="map-empty-hint">
          当前世界观还没有地图，请先在世界观地图界面创建 DND 战斗地图或 COC 调查地图。
        </p>

        <label class="field-block">
          房间名称
          <input v-model="roomName" placeholder="例如：第一章 · 雨夜旅店" />
        </label>

        <button class="btn btn-primary full-btn" :disabled="!selectedWorldId || creatingRoom" @click="createTrpgRoom">
          {{ creatingRoom ? '创建中...' : '创建跑团房间' }}
        </button>

        <form class="join-row" @submit.prevent="joinRoomById">
          <input v-model="joinRoomId" placeholder="输入房间 ID 加入" />
          <button class="btn btn-secondary" :disabled="!joinRoomId.trim()">加入</button>
        </form>

        <div v-if="currentRoom" class="room-card">
          <span>当前房间</span>
          <strong>{{ currentRoom.name }}</strong>
          <small>{{ currentRoom.id }}</small>
          <small v-if="currentRoom.linked_world_id">世界观：{{ currentWorld?.name || currentRoom.linked_world_id }}</small>
        </div>

        <div v-if="currentWorld" class="world-card-mini">
          <span>世界观概览</span>
          <strong>{{ currentWorld.name || '未命名世界观' }}</strong>
          <p>{{ currentWorld.description || '暂无描述' }}</p>
          <div class="world-mini-meta">
            <span>{{ currentWorld.entities?.length || 0 }} 实体</span>
            <span>{{ currentWorld.events?.length || 0 }} 事件</span>
          </div>
        </div>
      </aside>

      <main class="trpg-main card">
        <div class="panel-head">
          <div>
            <h2>{{ currentRoom?.name || '未进入跑团房间' }}</h2>
            <p>{{ currentRoom ? '房间事件会通过联机底座同步给所有成员。' : '创建或加入房间后开始跑团。' }}</p>
          </div>
          <span class="seq-badge">seq {{ latestSeq }}</span>
        </div>

        <section class="trpg-map-panel">
          <div class="map-panel-head">
            <div>
              <h3>{{ currentWorldMap?.name || '未选择地图' }}</h3>
              <p>{{ currentSystemLabel }} · {{ currentWorldMap?.description || '选择世界观地图后可在跑团中使用。' }}</p>
            </div>
            <span>{{ overlaySummaryText }}</span>
          </div>

          <div v-if="currentWorldMap" class="trpg-map-layout">
            <SquareGridMap
              v-if="currentWorldMapIsSquare"
              class="trpg-square-grid"
              :map="currentWorldMap"
              :cells="currentWorldMap.cells || []"
              :selected-ids="selectedMapCellId ? [selectedMapCellId] : []"
              :tokens="trpgOverlay.tokens"
              :cell-overlays="trpgOverlay.cellOverlays"
              @select-cell="handleMapCellSelect"
            />
            <HexGrid
              v-else
              class="trpg-hex-grid"
              :map="currentWorldMap"
              :cells="currentWorldMap.cells || []"
              :selected-ids="selectedMapCellId ? [selectedMapCellId] : []"
              :highlighted-ids="[]"
              :active-layer="systemType === 'coc' ? 'event' : 'terrain'"
              :tokens="trpgOverlay.tokens"
              :cell-overlays="trpgOverlay.cellOverlays"
              @select-cell="handleMapCellSelect"
            />

            <aside class="trpg-map-control">
              <div class="selected-cell-card">
                <span>选中格</span>
                <strong>{{ selectedMapCell?.name || selectedMapCell?.id || '未选择' }}</strong>
                <p>{{ selectedMapCell?.description || selectedMapCell?.notes || '点击地图格子后可编辑跑团覆盖层。' }}</p>
              </div>

              <section v-if="systemType === 'dnd'" class="map-control-section">
                <h4>DND Token</h4>
                <label>名称<input v-model="tokenForm.name" placeholder="角色 / 怪物名称" /></label>
                <label>类型
                  <select v-model="tokenForm.type">
                    <option value="pc">PC</option>
                    <option value="npc">NPC</option>
                    <option value="monster">怪物</option>
                  </select>
                </label>
                <div class="map-control-grid">
                  <label>HP<input v-model="tokenForm.hp" placeholder="12/20" /></label>
                  <label>AC<input v-model="tokenForm.ac" placeholder="15" /></label>
                </div>
                <label>状态<input v-model="tokenForm.status" placeholder="倒地、隐形、中毒..." /></label>
                <button class="btn btn-primary full-btn" :disabled="!selectedMapCellId || !tokenForm.name.trim()" @click="addDndToken">添加到选中格</button>
                <label>移动已有 Token
                  <select v-model="selectedTokenId">
                    <option value="">选择 Token</option>
                    <option v-for="token in trpgOverlay.tokens" :key="token.id" :value="token.id">{{ token.name }}</option>
                  </select>
                </label>
                <button class="btn btn-secondary full-btn" :disabled="!selectedTokenId || !selectedMapCellId" @click="moveSelectedToken">移动到选中格</button>
              </section>

              <section v-else class="map-control-section">
                <h4>COC 调查状态</h4>
                <label>状态
                  <select v-model="cocOverlayForm.status">
                    <option value="hidden">隐藏</option>
                    <option value="discovered">已发现</option>
                    <option value="resolved">已解析</option>
                    <option value="closed">已关闭</option>
                  </select>
                </label>
                <label>线索标题<input v-model="cocOverlayForm.title" placeholder="旧宅地下室的血迹" /></label>
                <label>说明<textarea v-model="cocOverlayForm.description" rows="3" placeholder="玩家已掌握的公开线索"></textarea></label>
                <label>NPC / 证物<input v-model="cocOverlayForm.npc" placeholder="NPC、证物或关联对象" /></label>
                <button class="btn btn-primary full-btn" :disabled="!selectedMapCellId" @click="updateCocCellOverlay">同步调查状态</button>
              </section>
            </aside>
          </div>

          <div v-else class="map-empty-state">
            <p>还没有可用地图。请先在世界观地图界面创建对应跑团地图，再回到房间使用。</p>
          </div>
        </section>

        <div class="event-log">
          <div v-if="events.length === 0" class="empty-state">暂无跑团事件。</div>
          <article v-for="event in events" :key="event.id" class="log-item" :class="eventClass(event)">
            <div class="log-type">{{ eventLabel(event) }}</div>
            <div class="log-content">
              <strong>{{ event.actor_id }}</strong>
              <p>{{ eventText(event) }}</p>
              <pre v-if="event.type === 'trpg.roll'" class="roll-detail">{{ event.payload?.summary }}</pre>
              <time>{{ formatTime(event.created_at) }}</time>
            </div>
          </article>
        </div>

        <div class="action-panels">
          <form class="message-box" @submit.prevent="sendMessage">
            <input v-model="messageText" :disabled="!currentRoom" placeholder="角色发言 / 玩家讨论" />
            <button class="btn btn-primary" :disabled="!currentRoom || !messageText.trim()">发送</button>
          </form>

          <form class="dice-box" @submit.prevent="rollDice">
            <input v-model="diceExpression" :disabled="!currentRoom" placeholder="d20 / 2d6+3" />
            <input v-model="diceReason" :disabled="!currentRoom" placeholder="检定说明，例如：潜行" />
            <button class="btn btn-secondary" :disabled="!currentRoom || !diceExpression.trim()">掷骰</button>
          </form>

          <form class="scene-box" @submit.prevent="postSceneNote">
            <textarea v-model="sceneNote" :disabled="!currentRoom" rows="3" placeholder="记录当前场景、线索、NPC反应或团长旁白..."></textarea>
            <button class="btn btn-secondary" :disabled="!currentRoom || !sceneNote.trim()">记录场景</button>
          </form>
        </div>
      </main>

      <aside class="trpg-side card">
        <div class="panel-head">
          <h2>成员</h2>
          <span>{{ members.length }} 人</span>
        </div>

        <form class="identity-card" @submit.prevent="saveDisplayName">
          <span>当前用户</span>
          <input v-model="displayNameDraft" placeholder="跑团昵称" />
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

        <section class="character-card-editor">
          <h3>角色卡快照</h3>
          <label>角色名<input v-model="characterForm.name" placeholder="角色名" /></label>
          <label>职业 / 身份<input v-model="characterForm.archetype" placeholder="调查员、战士、法师..." /></label>
          <label>HP / 状态<input v-model="characterForm.hp" placeholder="12/12，轻伤，理智稳定..." /></label>
          <label>备注<textarea v-model="characterForm.notes" rows="4" placeholder="属性、技能、装备、秘密、羁绊..."></textarea></label>
          <button class="btn btn-primary full-btn" :disabled="!currentRoom || !characterForm.name.trim()" @click="publishCharacter">同步角色卡</button>
        </section>
      </aside>
    </section>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { collabApi } from '../api/collab'
import { worldApi } from '../api/world'
import HexGrid from '../components/map/HexGrid.vue'
import SquareGridMap from '../components/map/SquareGridMap.vue'
import SvgIcon from '../components/ui/SvgIcon.vue'
import { ensureCollabIdentity, writeCollabDisplayName } from '../utils/collabIdentity.js'
import { rollDiceExpression } from '../utils/trpgDice.js'
import {
  applyTrpgMapOverlayEvent,
  createCocCellOverlay,
  createDndToken,
  createTrpgRoomOverlay,
  getWorldStructuredMaps,
  isSquareTrpgMap,
  recommendMapsForSystem,
  summarizeTrpgOverlay,
} from '../utils/trpgMap.js'

const route = useRoute()
const router = useRouter()
const worlds = ref([])
const selectedWorldId = ref(String(route.query.worldId || '').trim())
const systemType = ref(String(route.query.system || 'dnd').trim().toLowerCase() === 'coc' ? 'coc' : 'dnd')
const activeMapId = ref(String(route.query.mapId || '').trim())
const currentWorld = ref(null)
const currentRoom = ref(null)
const members = ref([])
const events = ref([])
const latestSeq = ref(0)
const loading = ref(false)
const creatingRoom = ref(false)
const error = ref('')
const syncStatus = ref('未连接')
const roomName = ref('')
const joinRoomId = ref(String(route.query.roomId || '').trim())
const messageText = ref('')
const diceExpression = ref('d20')
const diceReason = ref('')
const sceneNote = ref('')
const identity = ref(ensureCollabIdentity())
const displayNameDraft = ref(identity.value.displayName)
const characterForm = reactive({
  name: '',
  archetype: '',
  hp: '',
  notes: '',
})
const selectedMapCellId = ref('')
const selectedTokenId = ref('')
const trpgOverlay = ref(createTrpgRoomOverlay(systemType.value, activeMapId.value))
const tokenForm = reactive({ name: '', type: 'pc', hp: '', ac: '', status: '' })
const cocOverlayForm = reactive({ status: 'discovered', title: '', description: '', npc: '' })
let heartbeatTimer = null
let syncLoopToken = 0

const worldMaps = computed(() => getWorldStructuredMaps(currentWorld.value || {}))
const recommendedMaps = computed(() => recommendMapsForSystem(worldMaps.value, systemType.value))
const currentWorldMap = computed(() => worldMaps.value.find(map => map.id === activeMapId.value) || null)
const currentWorldMapIsSquare = computed(() => isSquareTrpgMap(currentWorldMap.value || {}))
const selectedMapCell = computed(() => (currentWorldMap.value?.cells || []).find(cell => cell.id === selectedMapCellId.value) || null)
const currentSystemLabel = computed(() => systemType.value === 'coc' ? 'COC 调查地图' : 'DND 战术地图')
const overlaySummaryText = computed(() => {
  const summary = summarizeTrpgOverlay(trpgOverlay.value)
  return systemType.value === 'coc'
    ? `${summary.discoveredCells}/${summary.overlayCellCount} 线索状态`
    : `${summary.tokenCount} Token`
})

function actorPayload() {
  return {
    user_id: identity.value.userId,
    display_name: identity.value.displayName,
  }
}

async function bootstrap() {
  loading.value = true
  error.value = ''
  try {
    const worldsRes = await worldApi.listWorlds()
    worlds.value = worldsRes.worlds || []
    if (!selectedWorldId.value && worlds.value.length) {
      selectedWorldId.value = worlds.value[0].id
    }

    const requestedRoomId = String(route.query.roomId || '').trim()
    if (requestedRoomId) {
      const roomRes = await collabApi.getRoom(requestedRoomId)
      await enterRoom(roomRes.room)
    }
  } catch (e) {
    error.value = e.message || 'TRPG 模块加载失败'
  } finally {
    loading.value = false
  }
}

function resetOverlayForCurrentMap() {
  selectedMapCellId.value = ''
  selectedTokenId.value = ''
  trpgOverlay.value = createTrpgRoomOverlay(systemType.value, activeMapId.value)
}

async function handleActiveMapChange() {
  resetOverlayForCurrentMap()
  if (currentRoom.value) {
    await publishMapOverlay()
  }
}

async function loadWorld(worldId) {
  const id = String(worldId || '').trim()
  currentWorld.value = null
  if (!id) return
  try {
    const res = await worldApi.getWorld(id)
    currentWorld.value = res.world
    if (!roomName.value && res.world?.name) {
      roomName.value = `${res.world.name} · 跑团房间`
    }
    const maps = getWorldStructuredMaps(res.world)
    if (!activeMapId.value || !maps.some(map => map.id === activeMapId.value)) {
      const firstRecommended = recommendMapsForSystem(maps, systemType.value)[0]
      activeMapId.value = firstRecommended?.id || ''
      resetOverlayForCurrentMap()
    }
  } catch (e) {
    error.value = '加载世界观失败：' + (e.message || '网络错误')
  }
}

async function createTrpgRoom() {
  if (!selectedWorldId.value) return
  creatingRoom.value = true
  error.value = ''
  try {
    const name = roomName.value.trim() || `${currentWorld.value?.name || '未命名世界观'} · 跑团房间`
    const res = await collabApi.createRoom({
      name,
      room_type: 'trpg',
      linked_world_id: selectedWorldId.value,
      settings: {
        module: 'trpg',
        system: systemType.value,
        world_name: currentWorld.value?.name || '',
        active_map_id: activeMapId.value,
      },
      ...actorPayload(),
    })
    await enterRoom(res.room)
  } catch (e) {
    error.value = '创建跑团房间失败：' + (e.message || '网络错误')
  } finally {
    creatingRoom.value = false
  }
}

async function joinRoomById() {
  const roomId = joinRoomId.value.trim()
  if (!roomId) return
  try {
    const res = await collabApi.getRoom(roomId)
    await enterRoom(res.room)
  } catch (e) {
    error.value = '加入房间失败：' + (e.message || '网络错误')
  }
}

async function enterRoom(room) {
  syncLoopToken += 1
  currentRoom.value = room
  joinRoomId.value = room.id
  const roomSettings = room.settings || {}
  if (roomSettings.system === 'dnd' || roomSettings.system === 'coc') {
    systemType.value = roomSettings.system
  }
  if (room.linked_world_id) {
    selectedWorldId.value = room.linked_world_id
  }
  if (roomSettings.active_map_id) {
    activeMapId.value = roomSettings.active_map_id
  }
  resetOverlayForCurrentMap()
  latestSeq.value = 0
  events.value = []
  syncStatus.value = '正在加入'
  await collabApi.joinRoom(room.id, actorPayload())
  await Promise.all([loadMembers(), pollEvents()])
  syncStatus.value = '已连接'
  router.replace({ name: 'TrpgRoom', query: { roomId: room.id, system: systemType.value, ...(selectedWorldId.value ? { worldId: selectedWorldId.value } : {}), ...(activeMapId.value ? { mapId: activeMapId.value } : {}) } })
  startSyncLoop(room.id)
}

async function loadMembers() {
  if (!currentRoom.value) return
  const res = await collabApi.listMembers(currentRoom.value.id)
  members.value = res.members || []
}

function mergeEvents(incoming = [], latest = 0) {
  const knownIds = new Set(events.value.map(event => event.id))
  const additions = incoming.filter(event => event?.id && !knownIds.has(event.id))
  if (additions.length) {
    events.value.push(...additions)
    additions.forEach(handleTrpgRoomEvent)
  }
  latestSeq.value = Math.max(latestSeq.value, Number(latest || 0), ...incoming.map(event => Number(event.seq || 0)))
}

function handleTrpgRoomEvent(event) {
  if (event?.type !== 'trpg.map.overlay.updated') return
  trpgOverlay.value = applyTrpgMapOverlayEvent(trpgOverlay.value, event.payload || {})
  if (trpgOverlay.value.mapId) {
    activeMapId.value = trpgOverlay.value.mapId
  }
}

async function pollEvents() {
  if (!currentRoom.value) return
  const res = await collabApi.listEvents(currentRoom.value.id, latestSeq.value, 100)
  mergeEvents(res.events || [], res.latest_seq)
}

async function appendTrpgEvent(type, payload = {}) {
  if (!currentRoom.value) return
  await collabApi.appendEvent(currentRoom.value.id, {
    type,
    user_id: identity.value.userId,
    payload: {
      ...payload,
      display_name: identity.value.displayName,
      world_id: selectedWorldId.value,
      room_type: 'trpg',
    },
  })
  await pollEvents()
}

async function publishMapOverlay(overlay = trpgOverlay.value) {
  trpgOverlay.value = {
    ...overlay,
    system: systemType.value,
    mapId: activeMapId.value,
    updatedAt: new Date().toISOString(),
  }
  await appendTrpgEvent('trpg.map.overlay.updated', { overlay: trpgOverlay.value })
}

function handleMapCellSelect({ cell }) {
  selectedMapCellId.value = cell?.id || ''
  const existing = trpgOverlay.value.cellOverlays?.[selectedMapCellId.value]
  if (existing && systemType.value === 'coc') {
    cocOverlayForm.status = existing.status || 'discovered'
    cocOverlayForm.title = existing.title || ''
    cocOverlayForm.description = existing.description || ''
    cocOverlayForm.npc = existing.npc || existing.evidence || ''
  }
}

async function addDndToken() {
  if (!selectedMapCellId.value || !tokenForm.name.trim()) return
  const token = createDndToken({
    ...tokenForm,
    cellId: selectedMapCellId.value,
  })
  await publishMapOverlay({
    ...trpgOverlay.value,
    tokens: [...(trpgOverlay.value.tokens || []), token],
  })
  tokenForm.name = ''
  tokenForm.hp = ''
  tokenForm.ac = ''
  tokenForm.status = ''
  selectedTokenId.value = token.id
}

async function moveSelectedToken() {
  if (!selectedTokenId.value || !selectedMapCellId.value) return
  await publishMapOverlay({
    ...trpgOverlay.value,
    tokens: (trpgOverlay.value.tokens || []).map(token => token.id === selectedTokenId.value ? { ...token, cellId: selectedMapCellId.value, updatedAt: new Date().toISOString() } : token),
  })
}

async function updateCocCellOverlay() {
  if (!selectedMapCellId.value) return
  const overlay = createCocCellOverlay({
    ...cocOverlayForm,
    cellId: selectedMapCellId.value,
    evidence: cocOverlayForm.npc,
  })
  await publishMapOverlay({
    ...trpgOverlay.value,
    cellOverlays: {
      ...(trpgOverlay.value.cellOverlays || {}),
      [selectedMapCellId.value]: overlay,
    },
  })
}

async function sendMessage() {
  const content = messageText.value.trim()
  if (!content || !currentRoom.value) return
  await collabApi.postMessage(currentRoom.value.id, content, { user_id: identity.value.userId })
  messageText.value = ''
  await pollEvents()
}

async function rollDice() {
  if (!currentRoom.value || !diceExpression.value.trim()) return
  try {
    const result = rollDiceExpression(diceExpression.value)
    await appendTrpgEvent('trpg.roll', {
      expression: result.expression,
      total: result.total,
      parts: result.parts,
      summary: result.summary,
      reason: diceReason.value.trim(),
    })
    diceReason.value = ''
  } catch (e) {
    error.value = e.message || '骰子表达式错误'
  }
}

async function postSceneNote() {
  const note = sceneNote.value.trim()
  if (!note || !currentRoom.value) return
  await appendTrpgEvent('trpg.scene.note', { note })
  sceneNote.value = ''
}

async function publishCharacter() {
  if (!currentRoom.value || !characterForm.name.trim()) return
  await appendTrpgEvent('trpg.character.updated', {
    character: {
      name: characterForm.name.trim(),
      archetype: characterForm.archetype.trim(),
      hp: characterForm.hp.trim(),
      notes: characterForm.notes.trim(),
      player: identity.value.displayName,
    },
  })
}

async function heartbeat() {
  if (!currentRoom.value) return
  await collabApi.heartbeat(currentRoom.value.id, { user_id: identity.value.userId })
  await loadMembers()
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

async function saveDisplayName() {
  identity.value = writeCollabDisplayName(displayNameDraft.value)
  displayNameDraft.value = identity.value.displayName
  if (currentRoom.value) {
    await collabApi.joinRoom(currentRoom.value.id, actorPayload())
    await loadMembers()
  }
}

function formatTime(value) {
  if (!value) return ''
  return new Date(value).toLocaleTimeString()
}

function eventLabel(event) {
  return {
    message: '发言',
    'member.joined': '加入',
    'member.left': '离开',
    'trpg.roll': '掷骰',
    'trpg.scene.note': '场景',
    'trpg.character.updated': '角色卡',
    'trpg.map.overlay.updated': '地图',
  }[event.type] || event.type
}

function eventClass(event) {
  return {
    'is-roll': event.type === 'trpg.roll',
    'is-scene': event.type === 'trpg.scene.note',
    'is-character': event.type === 'trpg.character.updated',
    'is-map': event.type === 'trpg.map.overlay.updated',
  }
}

function eventText(event) {
  const payload = event.payload || {}
  if (event.type === 'message') return payload.content || ''
  if (event.type === 'member.joined') return '加入了跑团房间'
  if (event.type === 'member.left') return '离开了跑团房间'
  if (event.type === 'trpg.roll') return `${payload.reason ? `${payload.reason}：` : ''}${payload.expression} = ${payload.total}`
  if (event.type === 'trpg.scene.note') return payload.note || ''
  if (event.type === 'trpg.character.updated') {
    const character = payload.character || {}
    return `${character.player || payload.display_name || '玩家'} 更新了角色卡：${character.name || '未命名角色'}${character.hp ? `（${character.hp}）` : ''}`
  }
  if (event.type === 'trpg.map.overlay.updated') {
    const overlay = payload.overlay || {}
    const summary = summarizeTrpgOverlay(overlay)
    return systemType.value === 'coc'
      ? `更新了调查地图状态：${summary.discoveredCells}/${summary.overlayCellCount} 个格子已公开`
      : `更新了战术地图：${summary.tokenCount} 个 Token`
  }
  return JSON.stringify(payload)
}

watch(selectedWorldId, worldId => {
  if (!currentRoom.value) {
    activeMapId.value = ''
    resetOverlayForCurrentMap()
  }
  loadWorld(worldId)
})

watch(systemType, () => {
  if (currentRoom.value) return
  const firstRecommended = recommendedMaps.value[0]
  activeMapId.value = firstRecommended?.id || ''
  resetOverlayForCurrentMap()
})

onMounted(async () => {
  await bootstrap()
  heartbeatTimer = setInterval(() => heartbeat().catch(() => {}), 10000)
})

onBeforeUnmount(() => {
  syncLoopToken += 1
  if (heartbeatTimer) clearInterval(heartbeatTimer)
})
</script>

<style scoped>
.trpg-page {
  max-width: 1440px;
  margin: 0 auto;
  padding: var(--spacing-2xl) var(--spacing-lg);
}

.trpg-hero {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
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

.back-link:hover { color: var(--wf-accent-hover); }
.trpg-hero h1 { margin-bottom: var(--spacing-sm); font-size: 2rem; }
.trpg-hero p { color: var(--wf-text-secondary); line-height: 1.7; }

.trpg-layout {
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr) 300px;
  gap: var(--spacing-lg);
  align-items: start;
}

.card { padding: var(--spacing-lg); }

.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-md);
}
.panel-head h2, .character-card-editor h3 { margin: 0; }
.panel-head span, .panel-head p, .room-card span, .room-card small, .world-card-mini span, .member-item small, .identity-card span, .identity-card small { color: var(--wf-text-muted); }

.field-block, .identity-card, .character-card-editor label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: var(--wf-text-secondary);
  margin-bottom: var(--spacing-md);
}

.field-block input, .field-block select, .join-row input, .message-box input, .dice-box input, .scene-box textarea, .identity-card input, .character-card-editor input, .character-card-editor textarea {
  width: 100%;
  min-width: 0;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--wf-border);
  background: rgba(255, 255, 255, 0.04);
  color: var(--wf-text-primary);
}

.full-btn { width: 100%; justify-content: center; }
.join-row { display: flex; gap: var(--spacing-sm); margin: var(--spacing-md) 0; }

.room-card, .world-card-mini, .identity-card, .character-card-editor {
  padding: 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--wf-border);
  background: rgba(255, 255, 255, 0.035);
  margin-top: var(--spacing-md);
}
.room-card, .world-card-mini { display: flex; flex-direction: column; gap: 5px; }
.world-card-mini p { color: var(--wf-text-secondary); line-height: 1.6; margin: 4px 0; }
.world-mini-meta { display: flex; gap: 8px; flex-wrap: wrap; }
.world-mini-meta span { padding: 3px 8px; border-radius: var(--radius-full); background: rgba(255,255,255,0.06); }
.map-maintain-link { display: inline-flex; margin: -4px 0 var(--spacing-sm); color: var(--wf-accent); font-size: 13px; text-decoration: none; }
.map-maintain-link:hover { color: var(--wf-accent-hover); }
.map-empty-hint { color: var(--wf-text-muted); font-size: 13px; line-height: 1.6; margin: 0 0 var(--spacing-md); }

.seq-badge { color: var(--wf-accent); font-family: var(--font-mono); }
.trpg-map-panel {
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.025);
  padding: var(--spacing-md);
  margin-bottom: var(--spacing-md);
}
.map-panel-head { display: flex; justify-content: space-between; align-items: flex-start; gap: var(--spacing-md); margin-bottom: var(--spacing-md); }
.map-panel-head h3 { margin: 0; }
.map-panel-head p, .map-panel-head span { color: var(--wf-text-muted); }
.trpg-map-layout { display: grid; grid-template-columns: minmax(0, 1fr) 280px; gap: var(--spacing-md); align-items: start; }
.trpg-map-layout :deep(.hex-grid-shell), .trpg-map-layout :deep(.square-map-scroll) { min-height: 420px; max-height: 520px; }
.trpg-map-layout :deep(.hex-grid) { height: 420px; }
.trpg-map-control { display: flex; flex-direction: column; gap: var(--spacing-md); }
.selected-cell-card, .map-control-section, .map-empty-state {
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-md);
  background: rgba(0, 0, 0, 0.16);
  padding: 12px;
}
.selected-cell-card span { color: var(--wf-text-muted); font-size: 12px; }
.selected-cell-card strong { display: block; margin: 4px 0; }
.selected-cell-card p, .map-empty-state p { color: var(--wf-text-secondary); line-height: 1.6; margin: 0; }
.map-control-section { display: flex; flex-direction: column; gap: 8px; }
.map-control-section h4 { margin: 0 0 4px; }
.map-control-section label { display: flex; flex-direction: column; gap: 5px; color: var(--wf-text-secondary); font-size: 13px; }
.map-control-section input, .map-control-section select, .map-control-section textarea {
  width: 100%;
  min-width: 0;
  padding: 8px 10px;
  border-radius: var(--radius-md);
  border: 1px solid var(--wf-border);
  background: rgba(255, 255, 255, 0.04);
  color: var(--wf-text-primary);
}
.map-control-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.event-log {
  min-height: 520px;
  max-height: 620px;
  overflow-y: auto;
  padding-right: 4px;
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-md);
  background: rgba(0, 0, 0, 0.18);
  margin-bottom: var(--spacing-md);
}

.empty-state { padding: var(--spacing-2xl); text-align: center; color: var(--wf-text-muted); }
.log-item { display: grid; grid-template-columns: 72px minmax(0, 1fr); gap: var(--spacing-md); padding: 12px 14px; border-bottom: 1px solid var(--wf-border); }
.log-type { color: var(--wf-accent); font-size: 12px; font-family: var(--font-mono); }
.log-content strong { color: var(--wf-text-primary); }
.log-content p { margin: 4px 0; color: var(--wf-text-secondary); line-height: 1.6; }
.log-content time { color: var(--wf-text-muted); font-size: 12px; }
.log-item.is-roll { background: rgba(255, 255, 175, 0.045); }
.log-item.is-scene { background: rgba(59, 130, 246, 0.045); }
.log-item.is-character { background: rgba(16, 185, 129, 0.045); }
.log-item.is-map { background: rgba(168, 85, 247, 0.045); }
.roll-detail { margin: 6px 0 0; color: var(--wf-accent); font-family: var(--font-mono); white-space: pre-wrap; }

.action-panels { display: flex; flex-direction: column; gap: var(--spacing-sm); }
.message-box, .dice-box { display: flex; gap: var(--spacing-sm); }
.scene-box { display: flex; flex-direction: column; gap: var(--spacing-sm); }

.member-item { display: flex; align-items: center; gap: var(--spacing-sm); padding: 10px 0; border-bottom: 1px solid var(--wf-border); }
.dot { width: 8px; height: 8px; border-radius: 50%; background: var(--wf-text-muted); }
.dot.online { background: #8ee6a2; box-shadow: 0 0 10px rgba(142, 230, 162, 0.5); }
.character-card-editor { display: flex; flex-direction: column; gap: var(--spacing-sm); }

.alert.error { padding: 12px 14px; border-radius: var(--radius-md); color: #ffb4b4; background: rgba(255, 82, 82, 0.10); border: 1px solid rgba(255, 82, 82, 0.25); margin-bottom: var(--spacing-md); }

@media (max-width: 1180px) {
  .trpg-layout, .trpg-map-layout { grid-template-columns: 1fr; }
  .message-box, .dice-box, .join-row { flex-direction: column; }
}
</style>
