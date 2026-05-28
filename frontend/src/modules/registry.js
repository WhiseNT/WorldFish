import { ref, computed } from 'vue'
import { modulesApi } from '../api/modules'

const modules = ref([])
const navigation = ref([])
const loading = ref(false)
const error = ref('')

function normalizeModule(row) {
  return {
    ...(row.manifest || {}),
    runtime: row.runtime || {},
    dependents: row.dependents || [],
    enabled_dependents: row.enabled_dependents || [],
    enabled: Boolean(row.runtime?.enabled),
    loaded: Boolean(row.runtime?.loaded),
    error: row.runtime?.error || '',
  }
}

export function useModuleRegistry() {
  const enabledModules = computed(() => modules.value.filter(item => item.enabled))

  async function refreshModules() {
    loading.value = true
    error.value = ''
    try {
      const res = await modulesApi.listModules()
      modules.value = (res.modules || []).map(normalizeModule)
      return modules.value
    } catch (e) {
      error.value = e.message || '模块列表加载失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function refreshNavigation() {
    const res = await modulesApi.getNavigation()
    navigation.value = res.navigation || []
    return navigation.value
  }

  async function refreshAll() {
    await refreshModules()
    await refreshNavigation()
  }

  function isModuleEnabled(id) {
    return modules.value.some(item => item.id === id && item.enabled)
  }

  return {
    modules,
    enabledModules,
    navigation,
    loading,
    error,
    refreshModules,
    refreshNavigation,
    refreshAll,
    isModuleEnabled,
  }
}
