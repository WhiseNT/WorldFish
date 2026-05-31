import service from './index'

// 世界观相关API
export const worldApi = {
  // 创建世界观
  createWorld: (data) => {
    return service.post('/api/world/create', data)
  },

  // 更新世界观
  updateWorld: (worldId, data) => {
    return service.put(`/api/world/${worldId}`, data)
  },
  
  // 从文本提取世界观信息（长文本可能需较长时间，可选 worldId 用于自动 RAG 索引）
  extractWorld: (text, worldId = '', options = {}) => {
    const payload = { text, ...options }
    if (worldId) payload.world_id = worldId
    return service.post('/api/world/extract', payload, { timeout: 1800000 })
  },

  // 从文件提取世界观信息（axios 自动处理 Content-Type 和 boundary，可选 worldId 用于自动 RAG 索引）
  extractWorldFromFile: (formData, worldId = '', options = {}) => {
    if (worldId) formData.append('world_id', worldId)
    Object.entries(options || {}).forEach(([key, value]) => formData.append(key, value))
    return service.post('/api/world/extract', formData, { timeout: 1800000 })
  },

  // 获取 LLM 配置状态
  getLlmConfig: () => {
    return service.get('/api/world/llm-config')
  },

  // 获取世界模板列表
  listWorldTemplates: () => {
    return service.get('/api/world/templates')
  },

  // 获取世界模板详情
  getWorldTemplate: (templateId) => {
    return service.get(`/api/world/templates/${templateId}`)
  },

  // 保存 LLM 配置
  saveLlmConfig: (data) => {
    return service.put('/api/world/llm-config', data)
  },

  // 测试 LLM 配置
  testLlmConfig: (data) => {
    return service.post('/api/world/llm-config/test', data)
  },

  // 获取 LLM 模型列表
  getLlmModels: (data) => {
    return service.post('/api/world/llm-config/models', data)
  },

  // 保存 LLM 高级参数
  saveLlmSettings: (settings) => {
    return service.put('/api/world/llm-config', { settings })
  },
  
  // 添加实体
  addEntity: (worldId, data) => {
    return service.post(`/api/world/${worldId}/entities`, data)
  },
  
  // 添加事件
  addEvent: (worldId, data) => {
    return service.post(`/api/world/${worldId}/events`, data)
  },
  
  // 获取世界观详情
  getWorld: (worldId) => {
    return service.get(`/api/world/${worldId}`)
  },

  // 列出所有世界观
  listWorlds: () => {
    return service.get('/api/world/list')
  },

  // 删除世界观
  deleteWorld: (worldId) => {
    return service.delete(`/api/world/${worldId}`)
  },

  // 列出解析任务
  listExtractTasks: (params = {}) => {
    return service.get('/api/world/extract/tasks', { params })
  },

  // 轮询提取进度
  getExtractProgress: (taskId) => {
    return service.get(`/api/world/extract/${taskId}/progress`)
  },

  // 删除扫描任务记录
  deleteExtractTask: (taskId) => {
    return service.delete(`/api/world/extract/${taskId}`)
  },

  // 请求暂停提取
  pauseExtract: (taskId) => {
    return service.post(`/api/world/extract/${taskId}/pause`)
  },

  // 继续提取
  resumeExtract: (taskId) => {
    return service.post(`/api/world/extract/${taskId}/resume`)
  },

  // 请求中断提取
  cancelExtract: (taskId) => {
    return service.post(`/api/world/extract/${taskId}/cancel`)
  },
}

export default worldApi
