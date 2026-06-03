<template>
  <div
    class="hex-grid-shell"
    @wheel.prevent="handleWheel"
    @mousedown="startPan"
    @mousemove="movePan"
    @mouseup="endPan"
    @mouseleave="endPan"
  >
    <svg class="hex-grid" :viewBox="viewBox">
      <g :transform="`translate(${pan.x} ${pan.y}) scale(${scale})`">
        <g
          v-for="cell in cells"
          :key="cell.id"
          class="hex-cell"
          :class="{ selected: selectedSet.has(cell.id), highlighted: highlightSet.has(cell.id) }"
          @click.stop="selectCell(cell, $event)"
        >
          <polygon
            :points="hexPoints(cell).points"
            :fill="cellFill(cell)"
            :stroke="cellStroke(cell)"
            :stroke-width="selectedSet.has(cell.id) ? 2.5 : 1"
          />
          <circle v-if="hasResource(cell)" :cx="hexPoints(cell).cx + hexSize * 0.35" :cy="hexPoints(cell).cy - hexSize * 0.35" r="4" fill="#f59e0b" />
          <circle v-if="cell.linked_map_id" :cx="hexPoints(cell).cx - hexSize * 0.35" :cy="hexPoints(cell).cy - hexSize * 0.35" r="4" fill="var(--wf-accent)" />
          <text
            v-if="cell.name"
            :x="hexPoints(cell).cx"
            :y="hexPoints(cell).cy + 4"
            text-anchor="middle"
            class="hex-label"
          >{{ cell.name }}</text>
          <g v-if="overlayForCell(cell)" class="hex-overlay-badge">
            <rect
              :x="hexPoints(cell).cx - 22"
              :y="hexPoints(cell).cy - 25"
              width="44"
              height="14"
              rx="7"
              :fill="overlayColor(overlayForCell(cell))"
            />
            <text
              :x="hexPoints(cell).cx"
              :y="hexPoints(cell).cy - 14"
              text-anchor="middle"
              class="hex-overlay-label"
            >{{ overlayLabel(overlayForCell(cell)) }}</text>
          </g>
          <g
            v-for="(token, tokenIndex) in tokensForCell(cell)"
            :key="token.id"
            class="hex-token"
          >
            <circle
              :cx="hexPoints(cell).cx - 12 + (tokenIndex * 12)"
              :cy="hexPoints(cell).cy + 18"
              r="8"
              :fill="tokenColor(token)"
            />
            <text
              :x="hexPoints(cell).cx - 12 + (tokenIndex * 12)"
              :y="hexPoints(cell).cy + 21"
              text-anchor="middle"
              class="hex-token-label"
            >{{ tokenInitials(token) }}</text>
          </g>
        </g>
      </g>
    </svg>
    <div class="hex-hint">滚轮缩放 · 拖拽移动 · Ctrl/Shift 多选</div>
  </div>
</template>

<script>
const EMPTY_FILL = 'rgba(255, 255, 255, 0.015)'
const EMPTY_STROKE = 'rgba(255, 255, 255, 0.16)'

const TERRAIN_COLORS = {
  unset: EMPTY_FILL,
  plain: 'rgba(132, 204, 22, 0.42)',
  forest: 'rgba(34, 197, 94, 0.55)',
  mountain: 'rgba(120, 113, 108, 0.58)',
  desert: 'rgba(234, 179, 8, 0.50)',
  snow: 'rgba(226, 232, 240, 0.58)',
  ocean: 'rgba(14, 165, 233, 0.48)',
  lake: 'rgba(56, 189, 248, 0.46)',
  river: 'rgba(6, 182, 212, 0.48)',
  swamp: 'rgba(101, 163, 13, 0.45)',
  city: 'rgba(168, 85, 247, 0.48)',
  ruins: 'rgba(168, 162, 158, 0.45)',
  special: 'rgba(244, 114, 182, 0.50)',
}

const STATUS_COLORS = {
  normal: EMPTY_FILL,
  war: '#fca5a5',
  occupied: '#fdba74',
  disaster: '#f87171',
  blocked: '#facc15',
  abandoned: '#9ca3af',
  unknown: '#cbd5e1',
  special: '#f0abfc',
}

function hashColor(value) {
  const text = String(value || '')
  if (!text) return EMPTY_FILL
  let hash = 0
  for (let i = 0; i < text.length; i++) hash = text.charCodeAt(i) + ((hash << 5) - hash)
  const hue = Math.abs(hash) % 360
  return `hsl(${hue}, 62%, 72%)`
}

export default {
  name: 'HexGrid',
  props: {
    map: { type: Object, default: null },
    cells: { type: Array, default: () => [] },
    selectedIds: { type: Array, default: () => [] },
    highlightedIds: { type: Array, default: () => [] },
    activeLayer: { type: String, default: 'terrain' },
    tokens: { type: Array, default: () => [] },
    cellOverlays: { type: Object, default: () => ({}) },
  },
  emits: ['select-cell'],
  data() {
    return {
      hexSize: 28,
      scale: 1,
      pan: { x: 40, y: 50 },
      isPanning: false,
      lastPoint: null,
    }
  },
  computed: {
    selectedSet() {
      return new Set(this.selectedIds)
    },
    highlightSet() {
      return new Set(this.highlightedIds)
    },
    viewBox() {
      return `0 0 960 620`
    },
  },
  methods: {
    hexCenter(cell) {
      const size = this.hexSize
      const q = Number(cell.q || 0)
      const r = Number(cell.r || 0)
      const rowOffset = Number(cell.row_offset || 0)
      return {
        cx: size * Math.sqrt(3) * (q + rowOffset),
        cy: size * 1.5 * r,
      }
    },
    hexPoints(cell) {
      const { cx, cy } = this.hexCenter(cell)
      const points = []
      for (let i = 0; i < 6; i++) {
        const angle = Math.PI / 180 * (60 * i - 30)
        points.push(`${cx + this.hexSize * Math.cos(angle)},${cy + this.hexSize * Math.sin(angle)}`)
      }
      return { cx, cy, points: points.join(' ') }
    },
    isEmptyCell(cell) {
      return !cell.color && !cell.name && !cell.description && (!cell.terrain || cell.terrain === 'unset') && (!cell.status || cell.status === 'normal') && !cell.faction && !(cell.resources || []).length && !(cell.locations || []).length
    },
    cellFill(cell) {
      if (cell.color) return cell.color
      if (this.highlightSet.has(cell.id)) return 'rgba(255, 255, 175, 0.16)'
      if (this.activeLayer === 'terrain') return TERRAIN_COLORS[cell.terrain] || TERRAIN_COLORS.special
      if (this.activeLayer === 'status') return STATUS_COLORS[cell.status] || STATUS_COLORS.special
      if (this.activeLayer === 'faction') return hashColor(cell.faction)
      if (this.activeLayer === 'resource') return (cell.resources || []).length ? 'rgba(255, 165, 2, 0.42)' : EMPTY_FILL
      if (this.activeLayer === 'event') return cell.linked_map_id ? 'rgba(255, 255, 175, 0.18)' : EMPTY_FILL
      return EMPTY_FILL
    },
    cellStroke(cell) {
      if (this.selectedSet.has(cell.id)) return 'var(--wf-accent)'
      if (cell.color || !this.isEmptyCell(cell)) return 'rgba(255, 255, 255, 0.28)'
      return EMPTY_STROKE
    },
    hasResource(cell) {
      return (cell.resources || []).length > 0
    },
    tokensForCell(cell) {
      return (this.tokens || []).filter(token => token.cellId === cell.id || token.cell_id === cell.id).slice(0, 4)
    },
    tokenColor(token) {
      if (token.color) return token.color
      if (token.type === 'monster') return '#ef4444'
      if (token.type === 'npc') return '#f59e0b'
      return '#38bdf8'
    },
    tokenInitials(token) {
      const name = String(token.name || '?').trim()
      return name.slice(0, 1).toUpperCase() || '?'
    },
    overlayForCell(cell) {
      return this.cellOverlays?.[cell.id] || null
    },
    overlayColor(overlay) {
      const status = String(overlay?.status || '').trim()
      if (status === 'resolved') return 'rgba(16, 185, 129, 0.88)'
      if (status === 'discovered') return 'rgba(59, 130, 246, 0.88)'
      if (status === 'closed') return 'rgba(107, 114, 128, 0.88)'
      return 'rgba(245, 158, 11, 0.88)'
    },
    overlayLabel(overlay) {
      const status = String(overlay?.status || '').trim()
      return ({ hidden: '隐藏', discovered: '发现', resolved: '解析', closed: '关闭' }[status]) || '线索'
    },
    selectCell(cell, event) {
      this.$emit('select-cell', { cell, append: event.ctrlKey || event.metaKey || event.shiftKey })
    },
    handleWheel(event) {
      const delta = event.deltaY > 0 ? -0.08 : 0.08
      this.scale = Math.max(0.45, Math.min(2.5, this.scale + delta))
    },
    startPan(event) {
      if (event.button !== 0) return
      this.isPanning = true
      this.lastPoint = { x: event.clientX, y: event.clientY }
    },
    movePan(event) {
      if (!this.isPanning || !this.lastPoint) return
      this.pan.x += event.clientX - this.lastPoint.x
      this.pan.y += event.clientY - this.lastPoint.y
      this.lastPoint = { x: event.clientX, y: event.clientY }
    },
    endPan() {
      this.isPanning = false
      this.lastPoint = null
    },
  },
}
</script>

<style scoped>
.hex-grid-shell {
  position: relative;
  width: 100%;
  min-height: 620px;
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: var(--wf-bg-card);
  cursor: grab;
}
.hex-grid-shell:active { cursor: grabbing; }
.hex-grid { width: 100%; height: 620px; display: block; }
.hex-cell polygon { transition: fill .15s ease, stroke .15s ease, opacity .15s ease; opacity: .95; }
.hex-cell:hover polygon { stroke: var(--wf-text-primary); stroke-width: 2; opacity: 1; }
.hex-cell.selected polygon { opacity: 1; }
.hex-label { font-size: 10px; fill: var(--wf-text-primary); pointer-events: none; font-weight: 700; paint-order: stroke; stroke: rgba(0, 0, 0, .82); stroke-width: 3px; }
.hex-token circle { stroke: rgba(0, 0, 0, .72); stroke-width: 1.5; }
.hex-token-label { font-size: 9px; fill: white; pointer-events: none; font-weight: 800; paint-order: stroke; stroke: rgba(0, 0, 0, .65); stroke-width: 2px; }
.hex-overlay-label { font-size: 8px; fill: white; pointer-events: none; font-weight: 800; }
.hex-hint { position: absolute; left: 14px; bottom: 12px; padding: 6px 10px; border-radius: var(--radius-full); background: rgba(0, 0, 0, 0.42); border: 1px solid var(--wf-border); color: var(--wf-text-secondary); font-size: 12px; }
</style>
