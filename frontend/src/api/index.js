import axios from 'axios'
import i18n from '../i18n'

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:5001',
  timeout: 1800000,
})

// 语言头注入
http.interceptors.request.use(
  cfg => {
    cfg.headers['Accept-Language'] = i18n.global.locale.value
    return cfg
  },
  err => Promise.reject(err),
)

// 统一错误处理 + success 字段校验
http.interceptors.response.use(
  res => {
    const body = res.data
    if (body && body.success === false) {
      const msg = body.error || body.message || 'Unknown API error'
      console.error('API failure:', msg)
      return Promise.reject(new Error(msg))
    }
    return body
  },
  err => {
    if (err.code === 'ECONNABORTED') console.error('Request timed out')
    if (err.message === 'Network Error') console.error('Network unreachable')
    const body = err.response?.data
    if (body && typeof body === 'object') {
      const normalized = new Error(body.message || body.error || err.message)
      normalized.status = err.response.status
      normalized.data = body
      return Promise.reject(normalized)
    }
    if (err.response) err.status = err.response.status
    return Promise.reject(err)
  },
)

/**
 * 指数退避重试封装
 */
export async function requestWithRetry(fn, tries = 3, baseMs = 1000) {
  for (let round = 0; round < tries; round++) {
    try {
      return await fn()
    } catch (err) {
      if (round === tries - 1) throw err
      console.warn(`Retry ${round + 1}/${tries} after ${baseMs * 2 ** round}ms`)
      await new Promise(r => setTimeout(r, baseMs * 2 ** round))
    }
  }
}

export default http
