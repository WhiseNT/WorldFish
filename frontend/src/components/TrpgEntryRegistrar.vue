<script setup>
import { onBeforeUnmount, onMounted } from 'vue'

const ENTRY_ID = 'trpg-room'

function registerEntry() {
  window.dispatchEvent(new CustomEvent('worldfish:special-entry:add', {
    detail: {
      id: ENTRY_ID,
      label: 'TRPG 跑团',
      description: '创建或加入局域网跑团房间，进行聊天、掷骰和角色卡同步',
      route: { name: 'TrpgRoom' },
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
