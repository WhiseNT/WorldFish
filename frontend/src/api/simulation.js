import http, { requestWithRetry } from './index'

// ── 生命周期 ──

export const createSimulation = (data) =>
  requestWithRetry(() => http.post('/api/simulation/create', data), 3, 1000)

export const prepareSimulation = (data) =>
  requestWithRetry(() => http.post('/api/simulation/prepare', data), 3, 1000)

export const getPrepareStatus = (data) =>
  http.post('/api/simulation/prepare/status', data)

export const startSimulation = (data) =>
  requestWithRetry(() => http.post('/api/simulation/start', data), 3, 1000)

export const stopSimulation = (data) =>
  http.post('/api/simulation/stop', data)

export const closeSimulationEnv = (data) =>
  http.post('/api/simulation/close-env', data)

// ── 查询 ──

export const getSimulation = (id) =>
  http.get(`/api/simulation/${id}`)

export const listSimulations = (projectId) =>
  http.get('/api/simulation/list', { params: projectId ? { project_id: projectId } : {} })

export const getSimulationHistory = (limit = 20) =>
  http.get('/api/simulation/history', { params: { limit } })

// ── 运行时状态 ──

export const getRunStatus = (id) =>
  http.get(`/api/simulation/${id}/run-status`)

export const getRunStatusDetail = (id) =>
  http.get(`/api/simulation/${id}/run-status/detail`)

export const getEnvStatus = (data) =>
  http.post('/api/simulation/env-status', data)

// ── Profiles & Config ──

export const getSimulationProfiles = (id) =>
  http.get(`/api/simulation/${id}/profiles`)

export const getSimulationProfilesRealtime = (id) =>
  http.get(`/api/simulation/${id}/profiles/realtime`)

export const getSimulationConfig = (id) =>
  http.get(`/api/simulation/${id}/config`)

export const getSimulationConfigRealtime = (id) =>
  http.get(`/api/simulation/${id}/config/realtime`)

// ── 动作 & 时间线 ──

export const getSimulationActions = (id, params = {}) =>
  http.get(`/api/simulation/${id}/actions`, { params })

export const getSimulationTimeline = (id, startRound = 0, endRound = null) => {
  const q = { start_round: startRound }
  if (endRound !== null) q.end_round = endRound
  return http.get(`/api/simulation/${id}/timeline`, { params: q })
}

// ── 采访 ──

export const interviewAgents = (data) =>
  requestWithRetry(() => http.post('/api/simulation/interview/batch', data), 3, 1000)

export const getAgentStats = (id) =>
  http.get(`/api/simulation/${id}/agent-stats`)
