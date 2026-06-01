#!/usr/bin/env node

const net = require('node:net')
const { spawn } = require('node:child_process')

const FRONTEND_PORT = Number(process.env.FRONTEND_PORT || 5567)
const BACKEND_PORT = Number(process.env.FLASK_PORT || process.env.BACKEND_PORT || 5568)
const BACKEND_HOST = process.env.FLASK_HOST || '0.0.0.0'
const npmCommand = process.platform === 'win32' ? 'npm.cmd' : 'npm'
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

function run(label, args, options = {}) {
  const child = spawn(npmCommand, args, {
    cwd: __dirname,
    stdio: 'inherit',
    shell: false,
    env: {
      ...process.env,
      FRONTEND_PORT: String(FRONTEND_PORT),
      BACKEND_PORT: String(BACKEND_PORT),
      FLASK_PORT: String(BACKEND_PORT),
      FLASK_HOST: BACKEND_HOST,
      ...options.env,
    },
  })

  children.push(child)

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

  console.log('正在启动 WorldFish...')
  console.log(`前端地址：http://localhost:${FRONTEND_PORT}`)
  console.log(`后端地址：http://localhost:${BACKEND_PORT}`)
  console.log('如需修改端口，可设置 FRONTEND_PORT 或 FLASK_PORT。\n')

  run('后端', ['run', 'backend'])
  run('前端', ['run', 'frontend'])
}

main().catch((error) => {
  console.error(error)
  stopAll()
  process.exit(1)
})
