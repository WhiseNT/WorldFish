<template>
  <AppLayout>
    <router-view v-slot="{ Component, route }">
      <keep-alive :include="['WorldBuilderView']" :max="8">
        <component :is="Component" :key="buildRouteCacheKey(route)" />
      </keep-alive>
    </router-view>
    <ExtractionTaskFloating />
    <AgentFloating />
  </AppLayout>
</template>

<script setup>
import AppLayout from './components/AppLayout.vue'
import AgentFloating from './components/AgentFloating.vue'
import ExtractionTaskFloating from './components/ExtractionTaskFloating.vue'

function buildRouteCacheKey(route) {
  if (route?.name === 'WorldBuilder') {
    const worldId = String(route?.query?.worldId || '').trim()
    return `WorldBuilder:${worldId || '__blank__'}`
  }
  if (route?.name) {
    return String(route.name)
  }
  return String(route?.fullPath || 'unknown')
}
</script>
