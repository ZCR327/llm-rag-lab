# stop_agent.ps1 - Gracefully stop the Streamlit launched by start_agent.ps1
# Usage:
#   powershell -ExecutionPolicy Bypass -File stop_agent.ps1

$ErrorActionPreference = 'Stop'
$Port = 8501
$conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue

if (-not $conn) {
    Write-Host ('[OK] Port ' + $Port + ' is free, nothing to stop') -ForegroundColor Green
    exit 0
}

$pidInUse = $conn.OwningProcess
$proc = Get-Process -Id $pidInUse -ErrorAction SilentlyContinue
if (-not $proc) {
    Write-Host ('[ERR] Found PID ' + $pidInUse + ' but process already exited') -ForegroundColor Red
    exit 1
}

if ($proc.ProcessName -notmatch 'python') {
    Write-Host ('[ERR] Port ' + $Port + ' is held by non-Python process (Name=' + $proc.ProcessName + '), will not touch') -ForegroundColor Red
    exit 1
}

Write-Host ('[..] Stopping Streamlit (PID=' + $pidInUse + ')...')
Stop-Process -Id $pidInUse

Start-Sleep -Seconds 1
$still = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($still) {
    Write-Host '[WARN] Port still held, force killing...' -ForegroundColor Yellow
    Stop-Process -Id $pidInUse -Force
    Start-Sleep -Seconds 1
}

$final = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($final) {
    Write-Host '[ERR] Failed to stop' -ForegroundColor Red
    exit 1
}

Write-Host '[OK] Streamlit stopped' -ForegroundColor Green
exit 0