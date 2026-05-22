<template>
  <AppLayout>
    <router-view />
    <AgentFloating />
  </AppLayout>
</template>

<script setup>
import AppLayout from './components/AppLayout.vue'
import AgentFloating from './components/AgentFloating.vue'
</script>
