#!/usr/bin/env node

const net = require('node:net')
const os = require('node:os')
const { spawn } = require('node:child_process')

const FRONTEND_PORT = Number(process.env.FRONTEND_PORT || 5567)
const BACKEND_PORT = Number(process.env.FLASK_PORT || process.env.BACKEND_PORT || 5568)
const BACKEND_HOST = process.env.FLASK_HOST || '0.0.0.0'
const children = []

function checkPort(port, host) {
  return new Promise((resolve) => {
    const server = net.createServer()

    server.once('error', (error) => {
      resolve({ ok: false, error })
    })

    server.once('listening', () => {
      server.close(() => resolve({ ok: true }))
    })

    server.listen(port, host)
  })
}

async function ensurePortAvailable(label, port, host) {
  const result = await checkPort(port, host)
  if (result.ok) return

  const reason = result.error && result.error.code ? result.error.code : 'UNKNOWN'
  console.error(`\n${label} 端口 ${port} 不可用（${reason}）。`)
  console.error('请关闭占用该端口的程序，或用环境变量指定其他端口，例如：')
  console.error(label === '前端'
    ? '  FRONTEND_PORT=5570 npm start'
    : '  FLASK_PORT=5571 npm start')
  process.exit(1)
}

function getLanAddresses() {
  const interfaces = os.networkInterfaces()
  const addresses = []

  for (const entries of Object.values(interfaces)) {
    for (const entry of entries || []) {
      if (!entry || entry.internal || entry.family !== 'IPv4') continue
      if (!entry.address || entry.address.startsWith('127.')) continue
      addresses.push(entry.address)
    }
  }

  return [...new Set(addresses)].sort()
}

function createChildEnv(extraEnv = {}) {
  const env = {}
  for (const [key, value] of Object.entries(process.env)) {
    if (!key || key.startsWith('=')) continue
    if (value === undefined || value === null) continue
    env[key] = String(value)
  }

  return {
    ...env,
    FRONTEND_PORT: String(FRONTEND_PORT),
    BACKEND_PORT: String(BACKEND_PORT),
    FLASK_PORT: String(BACKEND_PORT),
    FLASK_HOST: BACKEND_HOST,
    ...extraEnv,
  }
}

function run(label, command, options = {}) {
  const child = spawn(command, {
    cwd: __dirname,
    stdio: 'inherit',
    shell: true,
    windowsHide: false,
    env: createChildEnv(options.env),
  })

  children.push(child)

  child.on('error', (error) => {
    console.error(`${label} 启动失败：${error.message}`)
    stopAll()
    process.exit(1)
  })

  child.on('exit', (code, signal) => {
    if (signal) {
      console.log(`${label} 已停止：${signal}`)
      return
    }

    if (code && code !== 0) {
      console.error(`${label} 已退出，退出码：${code}`)
      stopAll()
      process.exit(code)
    }
  })

  return child
}

function canConnect(port, host) {
  return new Promise((resolve) => {
    const socket = net.createConnection({ port, host })
    socket.setTimeout(800)

    socket.once('connect', () => {
      socket.destroy()
      resolve(true)
    })

    socket.once('timeout', () => {
      socket.destroy()
      resolve(false)
    })

    socket.once('error', () => {
      socket.destroy()
      resolve(false)
    })
  })
}

async function waitForPortListening(label, port, host, timeoutMs = 30000) {
  const startedAt = Date.now()
  const intervalMs = 250

  while (Date.now() - startedAt < timeoutMs) {
    if (await canConnect(port, host)) {
      console.log(`${label} 已就绪：${host}:${port}`)
      return true
    }
    await new Promise(resolve => setTimeout(resolve, intervalMs))
  }

  console.error(`${label} 在 ${Math.round(timeoutMs / 1000)} 秒内没有就绪：${host}:${port}`)
  return false
}

function stopAll() {
  for (const child of children) {
    if (!child.killed) child.kill()
  }
}

process.on('SIGINT', () => {
  console.log('\n正在停止 WorldFish...')
  stopAll()
  process.exit(0)
})

process.on('SIGTERM', () => {
  stopAll()
  process.exit(0)
})

async function main() {
  await ensurePortAvailable('前端', FRONTEND_PORT, '0.0.0.0')
  await ensurePortAvailable('后端', BACKEND_PORT, BACKEND_HOST)

  const lanAddresses = getLanAddresses()

  console.log('正在启动 WorldFish...')
  console.log(`本机前端地址：http://localhost:${FRONTEND_PORT}`)
  console.log(`本机后端地址：http://127.0.0.1:${BACKEND_PORT}`)
  if (lanAddresses.length) {
    console.log('局域网联机地址：')
    lanAddresses.forEach((address) => {
      console.log(`  前端：http://${address}:${FRONTEND_PORT}`)
      console.log(`  后端：http://${address}:${BACKEND_PORT}`)
    })
    console.log('同一局域网内其他设备访问上述前端地址后，可进入“联机房间”复制或使用房间邀请链接。')
  } else {
    console.log('未检测到非本机 IPv4 地址；若需要局域网联机，请确认网络适配器已连接。')
  }
  console.log('如需修改端口，可设置 FRONTEND_PORT 或 FLASK_PORT。\n')

  run('后端', 'npm run backend')
  console.log('正在等待后端服务就绪...')
  const backendReady = await waitForPortListening('后端服务', BACKEND_PORT, '127.0.0.1')
  if (!backendReady) {
    stopAll()
    process.exit(1)
  }
  run('前端', 'npm run frontend')
}

main().catch((error) => {
  console.error(error)
  stopAll()
  process.exit(1)
})
