<template>
  <div class="language-switcher" ref="switcherRef">
    <button class="switcher-trigger" @click="toggleDropdown">
      {{ currentLabel }}
      <SvgIcon class="caret" :name="open ? 'chevron-up' : 'chevron-down'" :size="12" />
    </button>
    <ul v-if="open" class="switcher-dropdown">
      <li
        v-for="loc in availableLocales"
        :key="loc.key"
        class="switcher-option"
        :class="{ active: loc.key === locale }"
        @click="switchLocale(loc.key)"
      >
        {{ loc.label }}
      </li>
    </ul>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { availableLocales } from '@/i18n/index.js'
import SvgIcon from './ui/SvgIcon.vue'

const { locale } = useI18n()
const open = ref(false)
const switcherRef = ref(null)

const currentLabel = computed(() => {
  const found = availableLocales.find(l => l.key === locale.value)
  return found ? found.label : locale.value
})

const toggleDropdown = () => {
  open.value = !open.value
}

const switchLocale = (key) => {
  locale.value = key
  localStorage.setItem('locale', key)
  document.documentElement.lang = key
  open.value = false
}

const onClickOutside = (e) => {
  if (switcherRef.value && !switcherRef.value.contains(e.target)) {
    open.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', onClickOutside)
  document.documentElement.lang = locale.value
})

onUnmounted(() => {
  document.removeEventListener('click', onClickOutside)
})
</script>

<style scoped>
.language-switcher {
  position: relative;
  display: inline-block;
  font-family: 'JetBrains Mono', monospace;
}

.switcher-trigger {
  background: rgba(255, 255, 255, 0.04);
  color: var(--wf-text-secondary);
  border: 1px solid var(--wf-border-light);
  padding: 5px 12px;
  font-family: var(--font-mono);
  font-size: 0.8rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: border-color 0.2s, background 0.2s, color 0.2s;
}

.switcher-trigger:hover {
  border-color: var(--wf-accent);
  background: var(--wf-accent-muted);
  color: var(--wf-accent);
}

.caret {
  color: currentColor;
}

.switcher-dropdown {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 6px;
  background: rgba(17, 17, 19, 0.98);
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-md);
  list-style: none;
  padding: 4px;
  min-width: 100%;
  z-index: 1000;
  box-shadow: var(--shadow-md);
  backdrop-filter: blur(12px);
}

.switcher-option {
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  font-size: 0.8rem;
  color: var(--wf-text-secondary);
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.15s, color 0.15s;
}

.switcher-option:hover {
  background: rgba(255, 255, 255, 0.06);
  color: var(--wf-text-primary);
}

.switcher-option.active {
  color: var(--wf-accent);
  background: var(--wf-accent-muted);
}


</style>
