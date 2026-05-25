<template>
  <div class="world-map-editor">
    <section class="map-toolbar">
      <div class="map-list-block">
        <label>当前地图</label>
        <select v-model="currentMapId" class="toolbar-field" @change="loadCurrentMap">
          <option value="">选择地图</option>
          <option v-for="item in maps" :key="item.id" :value="item.id">
            {{ item.name }}{{ item.is_default ? '（默认）' : '' }}
          </option>
        </select>
      </div>
      <div class="map-actions">
        <button @click="showCreate = !showCreate">新建地图</button>
        <button :disabled="!currentMap" @click="duplicateMap">复制</button>
        <button :disabled="!currentMap" @click="setDefaultMap">设为默认</button>
        <button :disabled="!parentMap" @click="jumpToParentMap">返回上级</button>
        <button class="danger" :disabled="!currentMap" @click="deleteMap">删除</button>
      </div>
      <div class="layer-switcher">
        <button v-for="layer in layers" :key="layer.value" :class="{ active: activeLayer === layer.value }" @click="activeLayer = layer.value">
          {{ layer.label }}
        </button>
      </div>
    </section>

    <section v-if="showCreate" class="create-card">
      <input v-model="newMap.name" class="toolbar-field" placeholder="地图名称" />
      <select v-model="newMap.type" class="toolbar-field">
        <option value="world">世界地图</option>
        <option value="continent">大陆地图</option>
        <option value="country">国家地图</option>
        <option value="region">区域地图</option>
      </select>
      <input v-model.number="newMap.radius" type="number" min="1" max="12" class="toolbar-field small" title="六边形半径" />
      <button class="primary" :disabled="loading" @click="createMap">创建</button>
    </section>

    <p v-if="statusText" class="status-text">{{ statusText }}</p>

    <div v-if="currentMap" class="map-layout">
      <main class="map-main">
        <MapSearchPanel :loading="searching" :results="searchResults" @search="searchMap" @select-result="selectSearchResult" />
        <MapBatchEditor :selected-count="selectedIds.length" :saving="saving" @apply="applyBatchUpdate" />
        <HexGrid
          :map="currentMap"
          :cells="currentMap.cells || []"
          :selected-ids="selectedIds"
          :highlighted-ids="highlightedIds"
          :active-layer="activeLayer"
          @select-cell="handleSelectCell"
        />
      </main>
      <MapCellPanel
        :cell="selectedCell"
        :maps="maps"
        :current-map-id="currentMapId"
        :saving="saving"
        @save="saveCell"
        @jump-map="jumpToMap"
      />
    </div>

    <div v-else class="empty-map-state">
      <h3>还没有结构化地图</h3>
      <p>创建一张六边形地图后，就可以为区域标记地形、势力、资源、事件和状态。</p>
      <button class="primary" @click="showCreate = true">创建第一张地图</button>
    </div>
  </div>
</template>

<script>
import HexGrid from './HexGrid.vue'
import MapBatchEditor from './MapBatchEditor.vue'
import MapCellPanel from './MapCellPanel.vue'
import MapSearchPanel from './MapSearchPanel.vue'

export default {
  name: 'WorldMapEditor',
  components: { HexGrid, MapBatchEditor, MapCellPanel, MapSearchPanel },
  props: {
    worldId: { type: String, default: '' },
    initialMaps: { type: Array, default: () => [] },
  },
  emits: ['need-world-id', 'maps-change'],
  data() {
    return {
      maps: [],
      currentMapId: '',
      currentMap: null,
      selectedIds: [],
      highlightedIds: [],
      searchResults: [],
      activeLayer: 'terrain',
      loading: false,
      saving: false,
      searching: false,
      showCreate: false,
      statusText: '',
      newMap: { name: '世界地图', type: 'world', radius: 4 },
      layers: [
        { value: 'terrain', label: '地形' },
        { value: 'faction', label: '势力' },
        { value: 'resource', label: '资源' },
        { value: 'event', label: '区域图' },
        { value: 'status', label: '状态' },
      ],
    }
  },
  computed: {
    selectedCell() {
      if (!this.currentMap || !this.selectedIds.length) return null
      return (this.currentMap.cells || []).find(cell => cell.id === this.selectedIds[this.selectedIds.length - 1]) || null
    },
    parentMap() {
      if (!this.currentMap?.parent_map_id) return null
      return this.maps.find(map => map.id === this.currentMap.parent_map_id) || null
    },
  },
  watch: {
    initialMaps: {
      immediate: true,
      deep: true,
      handler(value) {
        this.maps = this.normalizeMaps(value || [])
        if (!this.currentMapId && this.maps.length) {
          const defaultMap = this.maps.find(item => item.is_default) || this.maps[0]
          this.currentMapId = defaultMap.id
        }
        this.loadCurrentMap()
      },
    },
  },
  methods: {
    async ensureWorldId() {
      if (this.worldId) return true
      this.$emit('need-world-id')
      for (let i = 0; i < 40; i += 1) {
        await new Promise(resolve => setTimeout(resolve, 100))
        if (this.worldId) return true
      }
      this.statusText = '请先保存世界观后再创建地图'
      return false
    },
    createLocalId(prefix) {
      return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`
    },
    normalizeMaps(maps) {
      const normalized = (Array.isArray(maps) ? maps : [])
        .filter(item => item && typeof item === 'object')
        .map(item => ({
          ...item,
          cells: Array.isArray(item.cells) ? item.cells.map(cell => ({ color: '', linked_map_id: '', ...cell })) : [],
          width: Number(item.width || ((Number(item.radius || 4) * 2) + 1)),
          height: Number(item.height || ((Number(item.radius || 4) * 2) + 1)),
          radius: Number(item.radius || Math.floor((Number(item.width || 9) - 1) / 2) || 4),
          parent_map_id: item.parent_map_id || '',
          parent_cell_id: item.parent_cell_id || '',
        }))
      if (normalized.length && !normalized.some(item => item.is_default)) normalized[0].is_default = true
      return normalized
    },
    emitMapsChange() {
      this.$emit('maps-change', this.maps)
    },
    loadCurrentMap() {
      if (!this.currentMapId) {
        this.currentMap = null
        return
      }
      const target = this.maps.find(item => item.id === this.currentMapId)
      this.currentMap = target || null
      this.selectedIds = []
      this.highlightedIds = []
      if (this.currentMap) this.statusText = `已加载：${this.currentMap.name}`
    },
    createCell(mapId, q, r, rowOffset = 0, axialQ = q, axialR = r) {
      return {
        id: `cell_${q}_${r}`,
        map_id: mapId,
        q,
        r,
        axial_q: axialQ,
        axial_r: axialR,
        row_offset: rowOffset,
        name: '',
        description: '',
        terrain: 'unset',
        status: 'normal',
        faction: '',
        resources: [],
        population: '',
        settlement: '',
        locations: [],
        linked_map_id: '',
        color: '',
        tags: [],
        notes: '',
        custom: {},
        updated_at: new Date().toISOString(),
      }
    },
    createHexagonCells(mapId, radius) {
      const cells = []
      const size = Math.max(1, Math.min(12, Number(radius || 4)))
      const maxRowLength = size * 2 + 1
      let index = 0
      for (let row = 0; row < maxRowLength; row += 1) {
        const distanceFromMiddle = Math.abs(row - size)
        const rowLength = maxRowLength - distanceFromMiddle
        const rowOffset = distanceFromMiddle / 2
        for (let col = 0; col < rowLength; col += 1) {
          const axialQ = col - Math.min(row, size)
          const axialR = row - size
          const cell = this.createCell(mapId, col, row, rowOffset, axialQ, axialR)
          cell.id = `cell_${index}`
          cells.push(cell)
          index += 1
        }
      }
      return cells
    },
    async createMap() {
      const ok = await this.ensureWorldId()
      if (!ok) return
      this.loading = true
      try {
        const radius = Math.max(1, Math.min(12, Number(this.newMap.radius || 4)))
        const width = radius * 2 + 1
        const height = radius * 2 + 1
        const id = this.createLocalId('map')
        const created = {
          id,
          world_id: this.worldId,
          name: String(this.newMap.name || '未命名地图').trim() || '未命名地图',
          description: '',
          type: this.newMap.type || 'world',
          width,
          height,
          radius,
          parent_map_id: this.selectedCell?.map_id || '',
          parent_cell_id: this.selectedCell?.id || '',
          is_default: this.maps.length === 0,
          view: { scale: 1, offset_x: 0, offset_y: 0 },
          layers: ['terrain', 'faction', 'resource', 'event', 'status'].map(type => ({ type, visible: type === 'terrain', rules: {}, field: type })),
          cells: this.createHexagonCells(id, radius),
          change_records: [],
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        }
        const maps = this.maps.map(item => ({ ...item, is_default: created.is_default ? false : item.is_default }))
        if (this.selectedCell) {
          const parentMapIndex = maps.findIndex(item => item.id === this.selectedCell.map_id)
          if (parentMapIndex >= 0) {
            maps[parentMapIndex] = {
              ...maps[parentMapIndex],
              cells: (maps[parentMapIndex].cells || []).map(cell => cell.id === this.selectedCell.id ? { ...cell, linked_map_id: id, updated_at: new Date().toISOString() } : cell)
            }
          }
        }
        maps.push(created)
        this.maps = maps
        this.currentMapId = created.id
        this.currentMap = created
        this.showCreate = false
        this.statusText = '地图已创建，点击“保存世界观”后持久化'
        this.emitMapsChange()
      } catch (error) {
        console.error('创建地图失败:', error)
        const message = error.message || '未知错误'
        this.statusText = `创建地图失败：${message}`
        alert(`创建地图失败：${message}`)
      } finally {
        this.loading = false
      }
    },
    duplicateMap() {
      if (!this.currentMap) return
      const id = this.createLocalId('map')
      const copied = JSON.parse(JSON.stringify(this.currentMap))
      copied.id = id
      copied.name = `${this.currentMap.name || '地图'} 副本`
      copied.is_default = false
      copied.created_at = new Date().toISOString()
      copied.updated_at = new Date().toISOString()
      copied.cells = (copied.cells || []).map(cell => ({ ...cell, map_id: id }))
      this.maps = [...this.maps, copied]
      this.currentMapId = id
      this.currentMap = copied
      this.emitMapsChange()
    },
    setDefaultMap() {
      if (!this.currentMap) return
      this.maps = this.maps.map(item => ({ ...item, is_default: item.id === this.currentMap.id }))
      this.currentMap = this.maps.find(item => item.id === this.currentMapId) || null
      this.emitMapsChange()
    },
    jumpToMap(mapId) {
      if (!mapId) return
      const target = this.maps.find(map => map.id === mapId)
      if (!target) return
      this.currentMapId = mapId
      this.loadCurrentMap()
    },
    jumpToParentMap() {
      if (!this.parentMap) return
      const parentCellId = this.currentMap.parent_cell_id
      this.currentMapId = this.parentMap.id
      this.loadCurrentMap()
      if (parentCellId) this.selectedIds = [parentCellId]
    },
    deleteMap() {
      if (!this.currentMap) return
      if (!confirm(`确定删除地图「${this.currentMap.name}」吗？`)) return
      this.maps = this.maps.filter(item => item.id !== this.currentMap.id)
      if (this.maps.length && !this.maps.some(item => item.is_default)) this.maps[0].is_default = true
      this.currentMapId = this.maps[0]?.id || ''
      this.loadCurrentMap()
      this.emitMapsChange()
    },
    handleSelectCell({ cell, append }) {
      if (append) {
        if (this.selectedIds.includes(cell.id)) {
          this.selectedIds = this.selectedIds.filter(id => id !== cell.id)
        } else {
          this.selectedIds = [...this.selectedIds, cell.id]
        }
      } else {
        this.selectedIds = [cell.id]
      }
    },
    replaceCells(updatedCells) {
      const byId = new Map((updatedCells || []).map(cell => [cell.id, cell]))
      this.currentMap.cells = (this.currentMap.cells || []).map(cell => byId.get(cell.id) || cell)
    },
    saveCell(payload) {
      if (!this.currentMap || !payload?.id) return
      const updated = { ...payload, updated_at: new Date().toISOString() }
      this.replaceCells([updated])
      this.currentMap.updated_at = new Date().toISOString()
      this.maps = this.maps.map(item => item.id === this.currentMap.id ? this.currentMap : item)
      this.statusText = '区域已实时更新，点击“保存世界观”后持久化'
      this.emitMapsChange()
    },
    applyBatchUpdate(updates) {
      if (!this.currentMap || !this.selectedIds.length) return
      if (this.selectedIds.length >= 12 && !confirm(`将修改 ${this.selectedIds.length} 个区域，确定继续吗？`)) return
      const selectedSet = new Set(this.selectedIds)
      const updatedCells = (this.currentMap.cells || []).map(cell => {
        if (!selectedSet.has(cell.id)) return cell
        const next = { ...cell }
        ;['terrain', 'status', 'faction', 'description', 'notes', 'color'].forEach(field => {
          if (updates[field] !== undefined) next[field] = updates[field]
        })
        if (updates.clear_faction) next.faction = ''
        if (updates.clear_resources) next.resources = []
        if (updates.clear_tags) next.tags = []
        if (Array.isArray(updates.resources)) next.resources = Array.from(new Set([...(next.resources || []), ...updates.resources]))
        if (Array.isArray(updates.tags)) next.tags = Array.from(new Set([...(next.tags || []), ...updates.tags]))
        next.updated_at = new Date().toISOString()
        return next
      })
      this.currentMap.cells = updatedCells
      this.currentMap.updated_at = new Date().toISOString()
      this.maps = this.maps.map(item => item.id === this.currentMap.id ? this.currentMap : item)
      this.statusText = `已修改 ${this.selectedIds.length} 个区域，点击“保存世界观”后持久化`
      this.emitMapsChange()
    },
    searchMap(query) {
      if (!this.currentMap) return
      const keyword = String(query || '').trim().toLowerCase()
      const results = (this.currentMap.cells || []).filter(cell => {
        if (!keyword) return true
        const haystack = [
          cell.id, cell.name, cell.description, cell.terrain, cell.status, cell.faction,
          ...(cell.resources || []), ...(cell.locations || []), ...(cell.tags || []),
          cell.color, cell.linked_map_id,
        ].join('\n').toLowerCase()
        return haystack.includes(keyword)
      }).slice(0, 100)
      this.searchResults = results.map(cell => ({
        id: cell.id,
        q: cell.q,
        r: cell.r,
        name: cell.name,
        terrain: cell.terrain,
        status: cell.status,
        faction: cell.faction,
        resources: cell.resources || [],
      }))
      this.highlightedIds = this.searchResults.map(item => item.id)
    },
    selectSearchResult(item) {
      this.selectedIds = [item.id]
      this.highlightedIds = [item.id]
    },
  },
}
</script>

<style scoped>
.world-map-editor { display: grid; gap: var(--spacing-md); color: var(--wf-text-primary); }
.map-toolbar, .create-card {
  display: flex;
  align-items: end;
  gap: 12px;
  flex-wrap: wrap;
  border: 1px solid var(--wf-border);
  background: var(--wf-bg-card);
  border-radius: var(--radius-lg);
  padding: var(--spacing-md);
  box-shadow: var(--shadow-sm);
}
.map-list-block { display: grid; gap: 6px; min-width: 220px; }
.map-list-block label { color: var(--wf-text-secondary); font-size: 13px; font-weight: 600; }
.toolbar-field {
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-md);
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--wf-bg-input);
  color: var(--wf-text-primary);
  outline: none;
}
.toolbar-field::placeholder { color: var(--wf-text-muted); }
.toolbar-field:focus { border-color: var(--wf-accent); box-shadow: 0 0 0 3px var(--wf-accent-muted); }
.toolbar-field option { background: var(--wf-dropdown-panel); color: var(--wf-text-primary); }
.toolbar-field option:checked,
.toolbar-field option:hover,
.toolbar-field option:focus { background: var(--wf-dropdown-option-active); }
.toolbar-field.small { width: 86px; }
.map-actions, .layer-switcher { display: flex; gap: 8px; flex-wrap: wrap; }
button {
  border: 1px solid var(--wf-border-light);
  border-radius: var(--radius-md);
  padding: var(--spacing-sm) var(--spacing-md);
  background: transparent;
  color: var(--wf-accent);
  font-weight: 600;
  cursor: pointer;
  min-height: 36px;
}
button:hover:not(:disabled) { background: var(--wf-accent-muted); border-color: var(--wf-accent); color: var(--wf-accent-hover); }
button.active, .primary { background: var(--wf-accent); color: var(--wf-text-on-accent); border-color: var(--wf-accent); }
button.danger { color: var(--wf-danger); }
button:disabled { opacity: .4; cursor: not-allowed; }
.status-text { margin: 0; color: var(--wf-text-muted); font-size: 13px; }
.map-layout { display: grid; grid-template-columns: minmax(0, 1fr) 340px; gap: 16px; align-items: start; }
.map-main { display: grid; gap: 12px; }
.empty-map-state {
  text-align: center;
  border: 1px dashed var(--wf-border-light);
  border-radius: var(--radius-xl);
  padding: var(--spacing-2xl);
  background: var(--wf-bg-card);
}
.empty-map-state h3 { margin: 0 0 var(--spacing-sm); color: var(--wf-text-primary); }
.empty-map-state p { color: var(--wf-text-secondary); }
@media (max-width: 1100px) { .map-layout { grid-template-columns: 1fr; } }
</style>
