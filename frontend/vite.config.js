import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

const frontendPort = Number(process.env.FRONTEND_PORT || 5567)
const backendPort = Number(process.env.FLASK_PORT || process.env.BACKEND_PORT || 5568)
const backendTarget = process.env.VITE_BACKEND_URL || `http://localhost:${backendPort}`

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
      '@locales': path.resolve(__dirname, '../locales')
    }
  },
  server: {
    port: frontendPort,
    open: true,
    proxy: {
      '/api': {
        target: backendTarget,
        changeOrigin: true,
        secure: false
      }
    }
  }
})
