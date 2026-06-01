#!/usr/bin/env sh

set -e

if ! command -v npm >/dev/null 2>&1; then
  echo "未找到 npm，请先安装 Node.js 18 或更高版本。"
  exit 1
fi

npm start
