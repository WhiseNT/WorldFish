@echo off
setlocal

where npm >nul 2>nul
if errorlevel 1 (
  echo 未找到 npm，请先安装 Node.js 18 或更高版本。
  pause
  exit /b 1
)

npm start
set EXIT_CODE=%ERRORLEVEL%

if not "%EXIT_CODE%"=="0" pause
exit /b %EXIT_CODE%
