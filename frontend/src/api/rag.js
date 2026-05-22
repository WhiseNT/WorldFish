import service from './index'

// RAG 向量知识库 API
export const ragApi = {
  // 添加文档到 RAG
  addDocuments: (worldId, data) => {
    return service.post(`/api/${worldId}/rag/documents`, data)
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
  uploadFile: (worldId, files, chunkSize = 800, chunkOverlap = 100) => {
    const formData = new FormData()
    for (const file of files) {
      formData.append('files', file)
    }
    formData.append('chunk_size', chunkSize)
    formData.append('chunk_overlap', chunkOverlap)
    return service.post(`/api/${worldId}/rag/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
}

export default ragApi
