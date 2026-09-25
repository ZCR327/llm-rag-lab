# start_agent.ps1 - Launch RAG agent Streamlit detached from bash tool
# Usage:
#   powershell -ExecutionPolicy Bypass -File start_agent.ps1
#   or double-click (right-click -> Run with PowerShell)
# Add to Task Scheduler for auto-start on boot
#
# Stop: see stop_agent.ps1

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogDir = Join-Path $ProjectRoot 'logs'
$LogFile = Join-Path $LogDir 'streamlit.log'
$ErrFile = Join-Path $LogDir 'streamlit.err.log'
$Port = 8501

# Check if port already in use
$existing = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($existing) {
    $pidInUse = $existing.OwningProcess
    $proc = Get-Process -Id $pidInUse -ErrorAction SilentlyContinue
    if ($proc -and $proc.ProcessName -match 'python') {
        Write-Host ('[OK] Streamlit already running (PID=' + $pidInUse + ', Port=' + $Port + '), no need to restart') -ForegroundColor Green
        Write-Host ('     Access: http://localhost:' + $Port)
        exit 0
    } else {
        Write-Host ('[ERR] Port ' + $Port + ' is held by a non-Python process (PID=' + $pidInUse + ')') -ForegroundColor Red
        Write-Host ('      Get-Process -Id ' + $pidInUse + ' | Stop-Process')
        exit 1
    }
}

# Prepare log dir
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

# Launch streamlit detached
$streamlitArgs = @(
    '-m', 'streamlit', 'run', 'app_streamlit.py',
    '--server.port', $Port,
    '--server.headless', 'true',
    '--server.address', '0.0.0.0',
    '--browser.gatherUsageStats', 'false'
)

Write-Host ('[..] Starting Streamlit (port ' + $Port + ')...') -ForegroundColor Cyan
Write-Host ('    cwd: ' + $ProjectRoot)
Write-Host ('    log: ' + $LogFile)

$proc = Start-Process -FilePath 'python' `
                      -ArgumentList $streamlitArgs `
                      -WorkingDirectory $ProjectRoot `
                      -RedirectStandardOutput $LogFile `
                      -RedirectStandardError $ErrFile `
                      -WindowStyle Hidden `
                      -PassThru

Write-Host ('[OK] Streamlit launched (PID=' + $proc.Id + ')') -ForegroundColor Green
Write-Host '     Waiting 5s for health check...'

Start-Sleep -Seconds 5

# Health check
$conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($conn) {
    Write-Host ('[OK] http://localhost:' + $Port + ' is listening') -ForegroundColor Green
    Write-Host ''
    Write-Host '=== Stop method ===' -ForegroundColor Yellow
    Write-Host '  powershell -ExecutionPolicy Bypass -File stop_agent.ps1'
    Write-Host ('  or: Get-Process -Id ' + $proc.Id + ' | Stop-Process')
    exit 0
} else {
    Write-Host '[ERR] Port not listening after launch, check logs:' -ForegroundColor Red
    Write-Host ('      ' + $LogFile)
    Write-Host ('      ' + $ErrFile)
    Write-Host ('      Process still running (PID=' + $proc.Id + '), cleanup: Get-Process -Id ' + $proc.Id + ' | Stop-Process')
    exit 1
}