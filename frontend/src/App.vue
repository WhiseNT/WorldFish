<template>
  <AppLayout>
    <router-view />
    <ExtractionTaskFloating />
    <AgentFloating />
  </AppLayout>
</template>

<script setup>
import AppLayout from './components/AppLayout.vue'
import AgentFloating from './components/AgentFloating.vue'
import ExtractionTaskFloating from './components/ExtractionTaskFloating.vue'
</script>
