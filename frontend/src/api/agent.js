import service from './index'

const BASE_PATH = '/api/agent'

function resolveAgentBase() {
  const baseURL = service.defaults.baseURL
  if (!baseURL) return BASE_PATH

  try {
    return new URL(BASE_PATH, `${String(baseURL).replace(/\/+$/, '')}/`).toString().replace(/\/$/, '')
  } catch {
    return BASE_PATH
  }
}

const BASE = resolveAgentBase()

/**
 * Agent API 封装
 * 支持 SSE 流式对话、Session 管理、MCP、文件上传等
 */

// ---- Session ----

export function listSessions(worldId = '') {
  return service.get(`${BASE}/sessions`, { params: { world_id: worldId } })
}

export function createSession(worldId = '', title = '') {
  return service.post(`${BASE}/sessions`, { world_id: worldId, title })
}

export function getSession(sessionId) {
  return service.get(`${BASE}/sessions/${sessionId}`)
}

export function deleteSession(sessionId) {
  return service.delete(`${BASE}/sessions/${sessionId}`)
}

export function updateSessionTitle(sessionId, title) {
  return service.put(`${BASE}/sessions/${sessionId}/title`, { title })
}

// ---- Runtime Settings ----

export function getAgentSettings() {
  return service.get(`${BASE}/settings`)
}

export function saveAgentSettings(settings) {
  return service.put(`${BASE}/settings`, settings)
}

// ---- Chat (SSE) ----

/**
 * 发送消息 — SSE 流式返回
 * @param {string} sessionId
 * @param {string} message
 * @param {string} worldId
 * @param {function} onChunk - (chunk) => void
 * @param {function} onDone - () => void
 * @param {function} onError - (error) => void
 * @returns {AbortController} 用于取消
 */
export function chatStream(sessionId, message, worldId = '', { onChunk, onDone, onError }) {
  const controller = new AbortController()

  fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, message, world_id: worldId }),
    signal: controller.signal,
  }).then(async (response) => {
    if (!response.ok) {
      const text = await response.text()
      onError(new Error(text))
      return
    }
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const chunk = JSON.parse(line.slice(6))
            onChunk(chunk)
            if (chunk.type === 'done') {
              onDone && onDone()
            }
          } catch (e) {
            // skip parse errors
          }
        }
      }
    }
  }).catch((err) => {
    if (err.name !== 'AbortError') {
      onError && onError(err)
    }
  })

  return controller
}

/**
 * 用户选择选项后继续对话
 */
export function respondToOptions(sessionId, selectedOptions, worldId = '', { onChunk, onDone, onError }) {
  const controller = new AbortController()

  fetch(`${BASE}/chat/respond`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, selected_options: selectedOptions, world_id: worldId }),
    signal: controller.signal,
  }).then(async (response) => {
    if (!response.ok) {
      const text = await response.text()
      onError(new Error(text))
      return
    }
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const chunk = JSON.parse(line.slice(6))
            onChunk(chunk)
            if (chunk.type === 'done') {
              onDone && onDone()
            }
          } catch (e) {}
        }
      }
    }
  }).catch((err) => {
    if (err.name !== 'AbortError') {
      onError && onError(err)
    }
  })

  return controller
}

// ---- File Upload ----

export function uploadFile(sessionId, files, worldId = '') {
  const formData = new FormData()
  formData.append('session_id', sessionId)
  if (worldId) formData.append('world_id', worldId)
  for (const file of files) {
    formData.append('files', file)
  }
  return service.post(`${BASE}/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// ---- Agent.md ----

export function getAgentMd(worldId = '') {
  const path = worldId ? `${BASE}/agent-md/${worldId}` : `${BASE}/agent-md`
  return service.get(path)
}

export function saveAgentMd(content, worldId = '') {
  const path = worldId ? `${BASE}/agent-md/${worldId}` : `${BASE}/agent-md`
  return service.put(path, { content, world_id: worldId })
}

// ---- Skills ----

export function listSkills(worldId = '') {
  const path = worldId ? `${BASE}/skills/${worldId}` : `${BASE}/skills`
  return service.get(path)
}

export function saveSkill(skill) {
  return service.post(`${BASE}/skills`, skill)
}

export function deleteSkill(skillId, worldId = '') {
  return service.delete(`${BASE}/skills/${skillId}`, { params: { world_id: worldId } })
}

export function discoverSkills() {
  return service.get(`${BASE}/skills/discover`)
}

export function toggleDiscoveredSkill(name, enabled) {
  return service.post(`${BASE}/skills/discover/toggle`, { name, enabled })
}

// ---- Memory ----

export function listMemories(worldId = '') {
  const path = worldId ? `${BASE}/memory/${worldId}` : `${BASE}/memory`
  return service.get(path)
}

export function setMemory(key, value, worldId = '') {
  return service.post(`${BASE}/memory`, { key, value, world_id: worldId })
}

export function deleteMemory(key, worldId = '') {
  return service.delete(`${BASE}/memory/${key}`, { params: { world_id: worldId } })
}

// ---- MCP ----

export function mcpCall(method, params = {}) {
  return service.post(`${BASE}/mcp`, {
    jsonrpc: '2.0',
    id: Date.now().toString(),
    method,
    params,
  })
}
