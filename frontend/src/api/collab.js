import http from './index'

export const collabApi = {
  bootstrap() {
    return http.get('/api/collab/bootstrap')
  },
  listWorkspaces() {
    return http.get('/api/collab/workspaces')
  },
  createWorkspace(data) {
    return http.post('/api/collab/workspaces', data)
  },
  listRooms(workspaceId = '') {
    const query = workspaceId ? `?workspace_id=${encodeURIComponent(workspaceId)}` : ''
    return http.get(`/api/collab/rooms${query}`)
  },
  createRoom(data) {
    return http.post('/api/collab/rooms', data)
  },
  getRoom(roomId) {
    return http.get(`/api/collab/rooms/${roomId}`)
  },
  joinRoom(roomId, data = {}) {
    return http.post(`/api/collab/rooms/${roomId}/join`, data)
  },
  leaveRoom(roomId, data = {}) {
    return http.post(`/api/collab/rooms/${roomId}/leave`, data)
  },
  heartbeat(roomId, data = {}) {
    return http.post(`/api/collab/rooms/${roomId}/heartbeat`, data)
  },
  listMembers(roomId) {
    return http.get(`/api/collab/rooms/${roomId}/members`)
  },
  listEvents(roomId, since = 0, limit = 100) {
    return http.get(`/api/collab/rooms/${roomId}/events?since=${since}&limit=${limit}`)
  },
  syncEvents(roomId, since = 0, limit = 100) {
    return http.get(`/api/collab/rooms/${roomId}/sync?since=${since}&limit=${limit}`, { timeout: 35000 })
  },
  health() {
    return http.get('/api/collab/health')
  },
  ensureWorldRoom(worldId, data = {}) {
    return http.post(`/api/collab/worlds/${worldId}/room`, data)
  },
  appendWorldEvent(worldId, data = {}) {
    return http.post(`/api/collab/worlds/${worldId}/events`, data)
  },
  appendEvent(roomId, data) {
    return http.post(`/api/collab/rooms/${roomId}/events`, data)
  },
  postMessage(roomId, content, data = {}) {
    return http.post(`/api/collab/rooms/${roomId}/messages`, { ...data, content })
  },
}

export default collabApi
