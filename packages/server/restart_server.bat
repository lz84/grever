@echo off
cd D:\work\research\agents-nexus\packages\server\src

echo Stopping existing uvicorn processes on 8097...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8097 ^| findstr LISTENING') do (
    taskkill /F /PID %%a 2>nul
)
timeout /t 2 /nobreak >nul

echo Starting new server on 192.168.1.9:8097 (with --reload)...
python -m uvicorn api.server:app --host 192.168.1.9 --port 8097 --reload
