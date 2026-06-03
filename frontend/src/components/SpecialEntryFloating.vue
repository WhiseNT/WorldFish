<template>
  <div v-if="SPECIAL_ENTRY_VISIBLE" class="special-entry-root">
    <button
      v-if="minimized"
      class="special-entry-mini-btn"
      type="button"
      title="打开特别入口"
      aria-label="打开特别入口"
      @click="minimized = false"
    >
      <SvgIcon name="grid" :size="20" />
      <span v-if="entries.length" class="special-entry-count">{{ entries.length }}</span>
    </button>

    <section v-else class="special-entry-window" aria-label="特别入口面板">
      <header class="special-entry-header">
        <div>
          <div class="special-entry-kicker">Special Entries</div>
          <h3>特别入口</h3>
        </div>
        <button class="special-entry-icon-btn" type="button" title="最小化" @click="minimized = true">
          <SvgIcon name="minus" :size="15" />
        </button>
      </header>

      <div class="special-entry-body">
        <div v-if="entries.length" class="special-entry-list">
          <button
            v-for="entry in entries"
            :key="entry.id"
            class="special-entry-action"
            type="button"
            @click="runEntry(entry)"
          >
            <span class="special-entry-action-main">
              <strong>{{ entry.label }}</strong>
              <small v-if="entry.description">{{ entry.description }}</small>
            </span>
            <SvgIcon name="chevron-right" :size="15" />
          </button>
        </div>
        <div v-else class="special-entry-empty">
          <strong>暂无特别入口</strong>
          <p>默认不会显示任何按钮。后续模块可以注册入口按钮显示在这里。</p>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import SvgIcon from './ui/SvgIcon.vue'

const SPECIAL_ENTRY_VISIBLE = false
const SET_ENTRIES_EVENT = 'worldfish:special-entries:set'
const ADD_ENTRY_EVENT = 'worldfish:special-entry:add'
const REMOVE_ENTRY_EVENT = 'worldfish:special-entry:remove'
const CLEAR_ENTRIES_EVENT = 'worldfish:special-entries:clear'

const router = useRouter()
const minimized = ref(true)
const entries = ref([])

function normalizeEntry(raw = {}) {
  const id = String(raw.id || raw.key || raw.label || '').trim()
  const label = String(raw.label || raw.title || '').trim()
  if (!id || !label) return null

  return {
    id,
    label,
    description: String(raw.description || raw.hint || '').trim(),
    route: raw.route || null,
    href: String(raw.href || '').trim(),
    onClick: typeof raw.onClick === 'function' ? raw.onClick : null,
  }
}

function setEntries(nextEntries = []) {
  entries.value = Array.isArray(nextEntries)
    ? nextEntries.map(normalizeEntry).filter(Boolean)
    : []
}

function addEntry(entry) {
  const normalized = normalizeEntry(entry)
  if (!normalized) return
  entries.value = [
    ...entries.value.filter(item => item.id !== normalized.id),
    normalized,
  ]
}

function handleSetEntries(event) {
  setEntries(event?.detail?.entries || [])
}

function handleAddEntry(event) {
  addEntry(event?.detail || {})
}

function handleRemoveEntry(event) {
  const id = String(event?.detail?.id || event?.detail || '').trim()
  if (!id) return
  entries.value = entries.value.filter(item => item.id !== id)
}

function handleClearEntries() {
  entries.value = []
}

function runEntry(entry) {
  if (entry.onClick) {
    entry.onClick(entry)
    return
  }

  if (entry.route) {
    router.push(entry.route)
    minimized.value = true
    return
  }

  if (entry.href) {
    window.open(entry.href, '_blank', 'noopener,noreferrer')
  }
}

onMounted(() => {
  window.addEventListener(SET_ENTRIES_EVENT, handleSetEntries)
  window.addEventListener(ADD_ENTRY_EVENT, handleAddEntry)
  window.addEventListener(REMOVE_ENTRY_EVENT, handleRemoveEntry)
  window.addEventListener(CLEAR_ENTRIES_EVENT, handleClearEntries)
})

onBeforeUnmount(() => {
  window.removeEventListener(SET_ENTRIES_EVENT, handleSetEntries)
  window.removeEventListener(ADD_ENTRY_EVENT, handleAddEntry)
  window.removeEventListener(REMOVE_ENTRY_EVENT, handleRemoveEntry)
  window.removeEventListener(CLEAR_ENTRIES_EVENT, handleClearEntries)
})
</script>

<style scoped>
.special-entry-root {
  position: fixed;
  right: 20px;
  bottom: 148px;
  z-index: 9997;
  font-family: var(--font-sans);
}

.special-entry-mini-btn {
  position: relative;
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  border: 1px solid var(--wf-border-light);
  background: rgba(17, 17, 19, 0.96);
  color: var(--wf-accent);
  cursor: pointer;
  box-shadow: var(--shadow-lg);
  transition: transform var(--transition-fast), border-color var(--transition-fast), background var(--transition-fast);
}

.special-entry-mini-btn:hover {
  transform: translateY(-2px) scale(1.04);
  border-color: rgba(255, 255, 175, 0.34);
  background: rgba(24, 24, 27, 0.98);
}

.special-entry-count {
  position: absolute;
  top: -3px;
  right: -3px;
  min-width: 18px;
  height: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: var(--wf-accent);
  color: var(--wf-text-on-accent);
  font-size: 11px;
  font-weight: 700;
  padding: 0 5px;
}

.special-entry-window {
  width: 320px;
  border: 1px solid var(--wf-border-light);
  border-radius: var(--radius-xl);
  background: rgba(17, 17, 19, 0.96);
  color: var(--wf-text-primary);
  box-shadow: var(--shadow-lg);
  overflow: hidden;
  backdrop-filter: blur(18px);
  animation: specialEntryIn 0.18s ease-out;
}

@keyframes specialEntryIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.special-entry-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-md);
  padding: 14px 16px;
  border-bottom: 1px solid var(--wf-border);
}

.special-entry-kicker {
  font-size: 11px;
  color: var(--wf-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.special-entry-header h3 {
  margin: 2px 0 0;
  font-size: 16px;
}

.special-entry-icon-btn {
  width: 30px;
  height: 30px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 0;
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.06);
  color: var(--wf-text-primary);
  cursor: pointer;
}

.special-entry-icon-btn:hover {
  background: rgba(255, 255, 255, 0.10);
}

.special-entry-body {
  padding: 14px;
}

.special-entry-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.special-entry-action {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-md);
  padding: 11px 12px;
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.035);
  color: var(--wf-text-primary);
  cursor: pointer;
  text-align: left;
  transition: background var(--transition-fast), border-color var(--transition-fast);
}

.special-entry-action:hover {
  background: rgba(255, 255, 255, 0.07);
  border-color: rgba(255, 255, 175, 0.28);
}

.special-entry-action-main {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.special-entry-action-main strong,
.special-entry-action-main small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.special-entry-action-main small {
  color: var(--wf-text-muted);
  font-size: 12px;
}

.special-entry-empty {
  min-height: 120px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 18px;
  border: 1px dashed var(--wf-border);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.025);
  text-align: center;
}

.special-entry-empty strong {
  color: var(--wf-text-primary);
}

.special-entry-empty p {
  margin: 0;
  color: var(--wf-text-muted);
  font-size: 13px;
  line-height: 1.6;
}

@media (max-width: 640px) {
  .special-entry-root {
    right: 16px;
    bottom: 142px;
  }

  .special-entry-window {
    width: min(320px, calc(100vw - 32px));
  }
}
</style>
