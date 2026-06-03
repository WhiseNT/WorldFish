<template>
  <div class="square-map-shell">
    <div class="square-map-scroll">
      <div class="square-board" :style="boardStyle">
        <img
          v-if="map?.background_image"
          class="square-bg-image"
          :src="map.background_image"
          :style="backgroundStyle"
          alt="地图背景"
          draggable="false"
        />
        <div class="square-grid-lines" :style="gridLineStyle"></div>
        <button
          v-for="cell in normalizedCells"
          :key="cell.id"
          type="button"
          class="square-cell"
          :class="{ selected: selectedSet.has(cell.id), marked: Boolean(cellOverlay(cell)) }"
          :style="cellStyle(cell)"
          @click.stop="selectCell(cell)"
        >
          <span v-if="cell.name" class="cell-name">{{ cell.name }}</span>
          <span v-if="cellOverlay(cell)" class="cell-status" :class="cellOverlay(cell).status">
            {{ overlayLabel(cellOverlay(cell)) }}
          </span>
        </button>
        <div
          v-for="token in visibleTokens"
          :key="token.id"
          class="square-token"
          :class="token.type"
          :style="tokenStyle(token)"
          :title="token.name"
        >
          {{ tokenInitials(token) }}
        </div>
      </div>
    </div>
    <div class="square-map-hint">方格地图 · 点击格子选择 · 在世界观地图界面上传背景图并调节对齐</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { normalizeMapView } from '../../utils/trpgMap.js'

const props = defineProps({
  map: { type: Object, default: null },
  cells: { type: Array, default: () => [] },
  selectedIds: { type: Array, default: () => [] },
  tokens: { type: Array, default: () => [] },
  cellOverlays: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['select-cell'])

const selectedSet = computed(() => new Set(props.selectedIds || []))
const view = computed(() => normalizeMapView(props.map?.view || {}))
const width = computed(() => Math.max(1, Number(props.map?.width || 12)))
const height = computed(() => Math.max(1, Number(props.map?.height || 12)))
const gridSize = computed(() => view.value.grid_size)
const normalizedCells = computed(() => {
  if (props.cells?.length) return props.cells
  const generated = []
  for (let row = 0; row < height.value; row += 1) {
    for (let col = 0; col < width.value; col += 1) {
      generated.push({ id: `cell_${col}_${row}`, q: col, r: row })
    }
  }
  return generated
})
const cellById = computed(() => new Map(normalizedCells.value.map(cell => [cell.id, cell])))
const visibleTokens = computed(() => (props.tokens || []).filter(token => cellById.value.has(token.cellId || token.cell_id)))

const boardStyle = computed(() => ({
  width: `${width.value * gridSize.value}px`,
  height: `${height.value * gridSize.value}px`,
}))
const backgroundStyle = computed(() => ({
  opacity: view.value.image_opacity,
  transform: `translate(${view.value.image_offset_x}px, ${view.value.image_offset_y}px) scale(${view.value.image_scale})`,
}))
const gridLineStyle = computed(() => ({
  backgroundSize: `${gridSize.value}px ${gridSize.value}px`,
  opacity: view.value.grid_opacity,
}))

function cellStyle(cell) {
  return {
    left: `${Number(cell.q || 0) * gridSize.value}px`,
    top: `${Number(cell.r || 0) * gridSize.value}px`,
    width: `${gridSize.value}px`,
    height: `${gridSize.value}px`,
  }
}

function tokenStyle(token) {
  const cell = cellById.value.get(token.cellId || token.cell_id)
  const q = Number(cell?.q || 0)
  const r = Number(cell?.r || 0)
  return {
    left: `${q * gridSize.value + gridSize.value / 2}px`,
    top: `${r * gridSize.value + gridSize.value / 2}px`,
  }
}

function cellOverlay(cell) {
  return props.cellOverlays?.[cell.id] || null
}

function overlayLabel(overlay) {
  return ({ hidden: '隐藏', discovered: '发现', resolved: '解析', closed: '关闭' }[overlay?.status]) || '线索'
}

function tokenInitials(token) {
  const name = String(token.name || '?').trim()
  return name.slice(0, 1).toUpperCase() || '?'
}

function selectCell(cell) {
  emit('select-cell', { cell, append: false })
}
</script>

<style scoped>
.square-map-shell {
  position: relative;
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-lg);
  background: var(--wf-bg-card);
  overflow: hidden;
}
.square-map-scroll {
  width: 100%;
  min-height: 520px;
  max-height: 680px;
  overflow: auto;
}
.square-board {
  position: relative;
  min-width: 100%;
  min-height: 520px;
  background: rgba(255, 255, 255, 0.018);
  overflow: hidden;
}
.square-bg-image {
  position: absolute;
  inset: 0 auto auto 0;
  width: 100%;
  height: 100%;
  object-fit: fill;
  transform-origin: top left;
  user-select: none;
  pointer-events: none;
}
.square-grid-lines {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background-image:
    linear-gradient(to right, rgba(255, 255, 255, 0.7) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(255, 255, 255, 0.7) 1px, transparent 1px);
}
.square-cell {
  position: absolute;
  border: 0;
  background: transparent;
  color: var(--wf-text-primary);
  cursor: pointer;
  padding: 0;
}
.square-cell:hover { outline: 2px solid rgba(255, 255, 175, 0.5); outline-offset: -2px; }
.square-cell.selected { outline: 2px solid var(--wf-accent); outline-offset: -2px; background: rgba(255, 255, 175, 0.10); }
.cell-name {
  position: absolute;
  left: 3px;
  bottom: 2px;
  max-width: calc(100% - 6px);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  font-size: 10px;
  color: white;
  text-shadow: 0 1px 3px rgba(0,0,0,0.9);
}
.cell-status {
  position: absolute;
  right: 3px;
  top: 3px;
  padding: 1px 5px;
  border-radius: var(--radius-full);
  color: white;
  background: rgba(245, 158, 11, 0.85);
  font-size: 10px;
  font-weight: 800;
}
.cell-status.discovered { background: rgba(59, 130, 246, 0.85); }
.cell-status.resolved { background: rgba(16, 185, 129, 0.85); }
.cell-status.closed { background: rgba(107, 114, 128, 0.85); }
.square-token {
  position: absolute;
  width: 24px;
  height: 24px;
  border-radius: 999px;
  transform: translate(-50%, -50%);
  display: grid;
  place-items: center;
  color: white;
  font-weight: 900;
  font-size: 12px;
  background: #38bdf8;
  border: 2px solid rgba(0, 0, 0, 0.65);
  box-shadow: 0 4px 10px rgba(0,0,0,0.35);
  pointer-events: none;
}
.square-token.npc { background: #f59e0b; }
.square-token.monster { background: #ef4444; }
.square-map-hint {
  position: absolute;
  left: 12px;
  bottom: 10px;
  padding: 5px 9px;
  border-radius: var(--radius-full);
  background: rgba(0,0,0,0.45);
  border: 1px solid var(--wf-border);
  color: var(--wf-text-secondary);
  font-size: 12px;
  pointer-events: none;
}
</style>
