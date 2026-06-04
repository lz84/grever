$env:VITE_API_BASE_URL = "http://localhost:8091"
$env:NODE_ENV = "development"
Set-Location "D:\work\research\agents-nexus\packages\ui"
npx vite --port 5173 --host 0.0.0.0
