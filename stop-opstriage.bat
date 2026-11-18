@echo off
title OpsTriage AI - Stopping Servers
echo ========================================================
echo               OpsTriage AI Stopper
echo ========================================================
echo.
echo Stopping OpsTriage AI servers on ports 8000 and 3000...

taskkill /FI "WINDOWTITLE eq OpsTriage - Backend*" /F /T >nul 2>&1
taskkill /FI "WINDOWTITLE eq OpsTriage - Frontend*" /F /T >nul 2>&1

:: Free up ports 8000 and 3000
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do taskkill /f /pid %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3000 ^| findstr LISTENING') do taskkill /f /pid %%a >nul 2>&1

echo.
echo All OpsTriage AI servers have been stopped.
echo ========================================================
timeout /t 3 >nul
