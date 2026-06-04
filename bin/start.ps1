# SYNOPSIS
# Nexus starts script
# DESCRIPTION
# Starts Nexus backend + frontend development servers
# Backend: http://localhost:8090 (API docs: http://localhost:8090/docs)
# Frontend: http://localhost:5173
# PARAMETER ServerOnly
# Start only backend, not frontend
# PARAMETER UIOnly
# Start only frontend, not backend
# PARAMETER Bg
# Background mode - logs to logs/ directory
# EXAMPLE
# .\bin\start.ps1              # Start backend + frontend
# .\bin\start.ps1 -ServerOnly  # Start only backend
# .\bin\start.ps1 -UIOnly      # Start only frontend
# .\bin\start.ps1 -Bg          # Background mode

param(
    [switch]$ServerOnly,
    [switch]$UIOnly,
    [switch]$Bg
)

$ErrorActionPreference = "Stop"
$nexusRoot = Split-Path $PSScriptRoot -Parent
$scriptsDir = Join-Path $nexusRoot "scripts"

# Check dependencies
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "Node.js not found. Please install Node.js" -ForegroundColor Red
    exit 1
}
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python not found. Please install Python" -ForegroundColor Red
    exit 1
}

# Check dev-runner.mjs
$devRunner = Join-Path $scriptsDir "dev-runner.mjs"
if (-not (Test-Path $devRunner)) {
    Write-Host "Start script not found: $devRunner" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Nexus Dev Environment" -ForegroundColor Cyan
Write-Host "  AI Agent Collaborative Platform" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Start Watchdog as a separate process
$watchdog = Join-Path $nexusRoot "scripts\watchdog.py"
if (Test-Path $watchdog) {
    Write-Host "Starting Watchdog (auto-restart on failure)..." -ForegroundColor Magenta
    Start-Process -FilePath "python" -ArgumentList "`"$watchdog`" --daemon" -WindowStyle Hidden
    Write-Host "Watchdog PID: $((Get-Process -Name python | Where-Object { $_.CommandLine -match 'watchdog' } | Select-Object -First 1).Id)" -ForegroundColor Gray
    Write-Host ""
}

if ($ServerOnly -and -not $UIOnly) {
    Write-Host "Starting backend service (port: 8090)..." -ForegroundColor Yellow
    Write-Host "API docs: http://localhost:8090/docs" -ForegroundColor Gray
    node $devRunner server
} elseif ($UIOnly -and -not $ServerOnly) {
    Write-Host "Starting frontend service (port: 5173)..." -ForegroundColor Yellow
    Write-Host "Access: http://localhost:5173" -ForegroundColor Gray
    node $devRunner ui
} else {
    Write-Host "Starting backend (8090) + frontend (5173)..." -ForegroundColor Yellow
    Write-Host "Frontend: http://localhost:5173" -ForegroundColor Gray
    Write-Host "API:      http://localhost:8090/docs" -ForegroundColor Gray
    Write-Host "Watchdog: monitoring both services" -ForegroundColor Magenta
    Write-Host "Ctrl+C to stop (watchdog keeps running)" -ForegroundColor Gray
    Write-Host ""
    node $devRunner all
}
