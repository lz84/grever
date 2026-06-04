@echo off
cd /d D:\work\research\agents-nexus\packages\ui
node .\node_modules\vite\bin\vite.js --port 5173 --host ::1 >> vite.log 2>&1
