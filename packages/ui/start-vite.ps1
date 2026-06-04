Set-Location 'D:\work\research\agents-nexus\packages\ui'
# Clear old log
if (Test-Path vite.log) { Clear-Content vite.log }
& node .\node_modules\vite\bin\vite.js --port 5173 --host ::1 *>> vite.log 2>&1
