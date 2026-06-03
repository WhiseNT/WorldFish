<script setup>
import { onBeforeUnmount, onMounted } from 'vue'

const ENTRY_ID = 'sillytavern-world-book-export'

function registerEntry() {
  window.dispatchEvent(new CustomEvent('worldfish:special-entry:add', {
    detail: {
      id: ENTRY_ID,
      label: 'SillyTavern 世界书',
      description: '将世界观导出为 SillyTavern World Info JSON',
      route: { name: 'SillyTavernWorldBookExport' },
    },
  }))
}

function removeEntry() {
  window.dispatchEvent(new CustomEvent('worldfish:special-entry:remove', {
    detail: { id: ENTRY_ID },
  }))
}

onMounted(registerEntry)
onBeforeUnmount(removeEntry)
</script>

<template></template>
