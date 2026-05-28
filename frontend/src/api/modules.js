import http from './index'

export const modulesApi = {
  listModules() {
    return http.get('/api/modules')
  },
  getNavigation() {
    return http.get('/api/modules/navigation')
  },
  getModule(id) {
    return http.get(`/api/modules/${id}`)
  },
  enableModule(id) {
    return http.post(`/api/modules/${id}/enable`)
  },
  disableModule(id, options = {}) {
    const query = options.cascade ? '?cascade=true' : ''
    return http.post(`/api/modules/${id}/disable${query}`)
  },
  reloadModule(id) {
    return http.post(`/api/modules/${id}/reload`)
  },
}

export default modulesApi
