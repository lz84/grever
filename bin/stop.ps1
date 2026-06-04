# SYNOPSIS
# Nexus stops script
# DESCRIPTION
# Stops Nexus backend and frontend services
# PARAMETER Force
# Forcefully terminates, skipping confirmation
# PARAMETER DryRun
# Preview mode - shows processes to terminate without stopping them
# EXAMPLE
# .\bin\stop.ps1           # Stops services (with confirmation)
# .\bin\stop.ps1 -Force    # Force stops
# .\bin\stop.ps1 -DryRun   # Preview mode

param(
    [switch]$Force,
    [switch]$DryRun
)

$ErrorActionPreference = "Continue"

$targets = @()

# 1. Find Nexus-related Python processes
$nexusPython = Get-CimInstance Win32_Process -Filter "Name LIKE '%python%'" 2>$null | Where-Object {
    $_.CommandLine -match 'nexus|reins|uvicorn.*8090|uvicorn.*8093' -and
    $_.CommandLine -notmatch 'openclaw' -and
    $_.ProcessId -ne $PID
}

foreach ($p in $nexusPython) {
    $cmdShort = if ($p.CommandLine.Length -gt 100) { $p.CommandLine.Substring(0, 100) + "..." } else { $p.CommandLine }
    $targets += [PSCustomObject]@{
        PID  = $p.ProcessId
        Name = "python"
        Cmd  = $cmdShort
    }
}

# 2. Find processes listening on ports 8090, 5173, 8093
foreach ($port in @(8090, 5173, 8093)) {
    $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    foreach ($c in $conns) {
        if ($c.OwningProcess -eq $PID) { continue }
        $already = $targets | Where-Object { $_.PID -eq $c.OwningProcess }
        if ($already) { continue }
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId = $($c.OwningProcess)" 2>$null
        if (-not $proc) { continue }
        $cmdShort = if ($proc.CommandLine) { if ($proc.CommandLine.Length -gt 100) { $proc.CommandLine.Substring(0, 100) + "..." } else { $proc.CommandLine } } else { "" }
        $targets += [PSCustomObject]@{
            PID  = $c.OwningProcess
            Name = $proc.Name
            Cmd  = $cmdShort
        }
    }
}

# 3. Find node processes (Vite frontend)
$nodeProcs = Get-CimInstance Win32_Process -Filter "Name LIKE '%node%'" 2>$null | Where-Object {
    $_.CommandLine -match 'vite|nexus.*ui' -and
    $_.ProcessId -ne $PID
}

foreach ($p in $nodeProcs) {
    $already = $targets | Where-Object { $_.PID -eq $p.ProcessId }
    if ($already) { continue }
    $cmdShort = if ($p.CommandLine.Length -gt 100) { $p.CommandLine.Substring(0, 100) + "..." } else { $p.CommandLine }
    $targets += [PSCustomObject]@{
        PID  = $p.ProcessId
        Name = "node"
        Cmd  = $cmdShort
    }
}

# Remove duplicates
$targets = $targets | Sort-Object -Property PID -Unique

if ($targets.Count -eq 0) {
    Write-Host "No Nexus services running" -ForegroundColor Green
    exit 0
}

$modeStr = if ($DryRun) { "Preview" } elseif ($Force) { "Force" } else { "Interactive" }
Write-Host ""
Write-Host "Nexus Service Cleanup ($modeStr)" -ForegroundColor Cyan
Write-Host ""
$targets | Format-Table PID, Name, Cmd -AutoSize | Out-String | Write-Host

if ($DryRun) {
    Write-Host "Preview mode - no actions taken. Use -Force to stop." -ForegroundColor Yellow
    exit 0
}

if (-not $Force) {
    $confirm = Read-Host "Stop $($targets.Count) service(s)? (y/n)"
    if ($confirm -ne "y") {
        Write-Host "Cancelled."
        exit 0
    }
}

# Stop
foreach ($t in $targets) {
    try {
        Stop-Process -Id $t.PID -Force -ErrorAction Stop
        Write-Host "  Stopped PID $($t.PID) ($($t.Name))" -ForegroundColor Green
    } catch {
        Write-Host "  Failed to stop PID $($t.PID): $_" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "Nexus services stopped" -ForegroundColor Green
