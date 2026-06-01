@echo off
setlocal
cd /d "%~dp0"

title WorldFish Launcher

echo ========================================
echo           WorldFish Launcher
echo ========================================
echo.

where npm >nul 2>nul
if errorlevel 1 (
  echo [ERROR] npm was not found.
  echo Please install Node.js 18 or newer.
  echo.
  pause
  exit /b 1
)

if not exist "node_modules" (
  echo [INFO] node_modules was not found.
  echo Please run: npm run setup:all
  echo.
  echo Current directory:
  echo %CD%
  echo.
  pause
  exit /b 1
)

if not exist "frontend\node_modules" (
  echo [INFO] frontend\node_modules was not found.
  echo Please run: npm run setup:all
  echo.
  pause
  exit /b 1
)

echo Starting WorldFish...
echo Frontend URL: http://localhost:5567
echo.

call npm start
set EXIT_CODE=%ERRORLEVEL%

echo.
if "%EXIT_CODE%"=="0" (
  echo WorldFish stopped.
) else (
  echo WorldFish exited with code %EXIT_CODE%.
)

echo.
pause
exit /b %EXIT_CODE%
