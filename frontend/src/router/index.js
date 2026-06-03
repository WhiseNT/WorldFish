import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import WorldBuilderView from '../views/WorldBuilderView.vue'
import { useModuleRegistry } from '../modules/registry'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home,
  },
  {
    path: '/world-builder',
    name: 'WorldBuilder',
    component: WorldBuilderView,
    meta: { moduleId: 'world-builder' },
  },
  {
    path: '/world-builder/templates/:templateId',
    name: 'WorldTemplateDetail',
    component: () => import('../views/WorldTemplateDetailView.vue'),
    props: true,
    meta: { moduleId: 'world-builder' },
  },
  {
    path: '/simulation/new',
    name: 'SimulationSetup',
    component: () => import('../views/SimulationSetup.vue'),
    meta: { moduleId: 'simulation' },
  },
  {
    path: '/simulation/:id',
    name: 'SimulationEvolution',
    component: () => import('../views/SimulationEvolution.vue'),
    props: true,
    meta: { moduleId: 'simulation' },
  },
  {
    path: '/trpg',
    name: 'TrpgRoom',
    component: () => import('../views/TrpgRoomView.vue'),
    meta: { moduleId: 'trpg' },
  },
  {
    path: '/rag',
    name: 'RagView',
    component: () => import('../views/RagView.vue'),
    meta: { moduleId: 'rag' },
  },
  {
    path: '/exports/sillytavern-world-book',
    name: 'SillyTavernWorldBookExport',
    component: () => import('../views/SillyTavernWorldBookExportView.vue'),
    meta: { moduleId: 'world-builder' },
  },
  {
    path: '/collab',
    name: 'Collab',
    component: () => import('../views/CollabView.vue'),
    meta: { moduleId: 'collaboration' },
  },
  {
    path: '/settings/llm',
    name: 'LlmConfig',
    component: () => import('../views/LlmConfigView.vue'),
    meta: { moduleId: 'settings' },
  },
  {
    path: '/settings/modules',
    name: 'Modules',
    component: () => import('../views/ModulesView.vue'),
    meta: { moduleId: 'settings' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async to => {
  const moduleId = to.meta?.moduleId
  if (!moduleId) return true
  if (moduleId === 'settings') return true

  const { modules, refreshModules, isModuleEnabled } = useModuleRegistry()
  if (!modules.value.length) {
    try {
      await refreshModules()
    } catch (e) {
      return true
    }
  }
  if (!isModuleEnabled(moduleId)) {
    return { path: '/settings/modules', query: { disabled: moduleId, redirect: to.fullPath } }
  }
  return true
})

export default router
