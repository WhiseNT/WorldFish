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
  disableModule(id) {
    return http.post(`/api/modules/${id}/disable`)
  },
  reloadModule(id) {
    return http.post(`/api/modules/${id}/reload`)
  },
}

export default modulesApi
