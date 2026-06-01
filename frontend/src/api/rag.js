import service from './index'

// RAG 向量知识库 API
export const ragApi = {
  // 获取切分预设
  getChunkPresets: () => {
    return service.get('/api/rag/chunk-presets')
  },

  // 添加文档到 RAG
  addDocuments: (worldId, data) => {
    return service.post(`/api/${worldId}/rag/documents`, data)
  },

  // 创建异步索引任务（可轮询真实 Embedding 进度）
  createIndexTask: (worldId, data) => {
    return service.post(`/api/${worldId}/rag/index-task`, data)
  },

  // 查询异步索引任务进度
  getIndexTask: (worldId, taskId) => {
    return service.get(`/api/${worldId}/rag/index-task/${taskId}`)
  },

  // 列出 RAG 中的文档
  listDocuments: (worldId, params = {}) => {
    return service.get(`/api/${worldId}/rag/documents`, { params })
  },

  // 删除 RAG 中的单个文档
  deleteDocument: (worldId, docId) => {
    return service.delete(`/api/${worldId}/rag/documents/${docId}`)
  },

  // 语义检索 RAG
  search: (worldId, data) => {
    return service.post(`/api/${worldId}/rag/search`, data)
  },

  // 获取 RAG 统计信息
  getStats: (worldId) => {
    return service.get(`/api/${worldId}/rag/stats`)
  },

  // 清空 RAG
  clear: (worldId) => {
    return service.delete(`/api/${worldId}/rag/clear`)
  },

  // 上传文件到 RAG
  uploadFile: (worldId, files, chunkPreset = 'novel') => {
    const formData = new FormData()
    for (const file of files) {
      formData.append('files', file)
    }
    formData.append('chunk_preset', chunkPreset)
    return service.post(`/api/${worldId}/rag/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
}

export default ragApi
