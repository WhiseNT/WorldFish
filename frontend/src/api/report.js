import http, { requestWithRetry } from './index'

export const generateReport = (data) =>
  requestWithRetry(() => http.post('/api/report/generate', data), 3, 1000)

export const getReportStatus = (reportId) =>
  http.get('/api/report/generate/status', { params: { report_id: reportId } })

export const getAgentLog = (reportId, fromLine = 0) =>
  http.get(`/api/report/${reportId}/agent-log`, { params: { from_line: fromLine } })

export const getConsoleLog = (reportId, fromLine = 0) =>
  http.get(`/api/report/${reportId}/console-log`, { params: { from_line: fromLine } })

export const getReport = (reportId) =>
  http.get(`/api/report/${reportId}`)

export const chatWithReport = (data) =>
  requestWithRetry(() => http.post('/api/report/chat', data), 3, 1000)
