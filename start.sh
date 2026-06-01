#!/usr/bin/env sh

set -e

cd "$(dirname "$0")"

if ! command -v npm >/dev/null 2>&1; then
  echo "未找到 npm，请先安装 Node.js 18 或更高版本。"
  exit 1
fi

if [ ! -d "node_modules" ] || [ ! -d "frontend/node_modules" ]; then
  echo "未找到依赖目录，请先运行："
  echo "  npm run setup:all"
  exit 1
fi

npm start
