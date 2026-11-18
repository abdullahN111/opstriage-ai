@echo off
title OpsTriage AI - Starting Servers
echo ========================================================
echo               OpsTriage AI Launcher
echo ========================================================
echo.
echo 1. Starting FastAPI Backend on port 8000...
start "OpsTriage - Backend" /min cmd /c "cd /d "%~dp0backend" && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

echo 2. Starting Next.js Frontend on port 3000...
start "OpsTriage - Frontend" /min cmd /c "cd /d "%~dp0frontend" && npm run dev"

echo.
echo 3. Waiting a few seconds for services to become ready...
timeout /t 5 /nobreak >nul

echo.
echo 4. Opening OpsTriage AI Command Center in your browser...
start http://localhost:3000

echo.
echo ========================================================
echo  OpsTriage AI is now running!
echo  - Frontend: http://localhost:3000
echo  - Backend:  http://localhost:8000
echo.
echo  To stop the servers later, double-click 'stop-opstriage.bat'
echo ========================================================
timeout /t 4 >nul
