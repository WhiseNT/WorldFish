import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import WorldBuilderView from '../views/WorldBuilderView.vue'

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
  },
  {
    path: '/simulation/new',
    name: 'SimulationSetup',
    component: () => import('../views/SimulationSetup.vue'),
  },
  {
    path: '/simulation/:id',
    name: 'SimulationEvolution',
    component: () => import('../views/SimulationEvolution.vue'),
    props: true,
  },
  {
    path: '/rag',
    name: 'RagView',
    component: () => import('../views/RagView.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
