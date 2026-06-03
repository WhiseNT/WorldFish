const fs = require('fs')
const path = require('path')

const root = path.resolve(__dirname, '..')

const ignoredDirs = new Set([
  '.git',
  'node_modules',
  'frontend/node_modules',
  'backend/.venv',
  'dist',
  'frontend/dist',
  '.pytest_cache',
  '__pycache__',
  'tmp',
])

const forbiddenPathPatterns = [
  /^cloud([/\\]|$)/,
  /^apps[/\\]cloud-/,
  /^backend[/\\]app[/\\]cloud([/\\]|$)/,
  /^frontend[/\\]src[/\\]cloud([/\\]|$)/,
  /^infra[/\\]cloud([/\\]|$)/,
  /^cloud-web([/\\]|$)/,
  /^cloud-api([/\\]|$)/,
  /^cloud-worker([/\\]|$)/,
]

const forbiddenImplementationHints = [
  'CloudBilling',
  'CloudMarketplace',
  'CloudRealtime',
  'CloudStorage',
  'CloudAIOrchestrator',
  'cloud billing',
  'cloud marketplace',
]

const allowedTextFiles = new Set([
  'docs/repository-boundary.md',
  'scripts/check-open-source-boundary.js',
])

function toRepoPath(filePath) {
  return path.relative(root, filePath).replace(/\\/g, '/')
}

function shouldIgnoreDir(dirPath) {
  const repoPath = toRepoPath(dirPath)
  if (!repoPath) return false
  if (ignoredDirs.has(repoPath)) return true
  return repoPath.split('/').some(part => ignoredDirs.has(part) || part === '.venv' || part === '__pycache__')
}

function walk(dirPath, files = []) {
  for (const entry of fs.readdirSync(dirPath, { withFileTypes: true })) {
    const fullPath = path.join(dirPath, entry.name)
    if (entry.isDirectory()) {
      if (!shouldIgnoreDir(fullPath)) walk(fullPath, files)
    } else if (entry.isFile()) {
      files.push(fullPath)
    }
  }
  return files
}

function isProbablyText(filePath) {
  const ext = path.extname(filePath).toLowerCase()
  return ['.js', '.ts', '.vue', '.py', '.json', '.md', '.yml', '.yaml', '.toml', '.env', '.sh', '.bat'].includes(ext)
}

const violations = []
const files = walk(root)

for (const filePath of files) {
  const repoPath = toRepoPath(filePath)
  if (forbiddenPathPatterns.some(pattern => pattern.test(repoPath))) {
    violations.push(`${repoPath}: 禁止在主仓库放置云平台实现路径`)
    continue
  }

  if (!isProbablyText(filePath) || allowedTextFiles.has(repoPath)) continue

  const content = fs.readFileSync(filePath, 'utf8')
  for (const hint of forbiddenImplementationHints) {
    if (content.includes(hint)) {
      violations.push(`${repoPath}: 出现云平台实现标识 ${hint}`)
    }
  }
}

if (violations.length) {
  console.error('WorldFish 主仓库只允许开源本地项目内容，发现以下边界违规：')
  for (const violation of violations) console.error(`- ${violation}`)
  process.exit(1)
}

console.log('开源本地项目边界检查通过。')
