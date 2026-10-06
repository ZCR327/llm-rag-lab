# test_worker.ps1 - Test Cloudflare Worker KV connectivity
#
# Usage:  powershell -ExecutionPolicy Bypass -File test_worker.ps1
#
# Why this script exists:
#   This machine uses a local proxy (127.0.0.1:7890) but PowerShell's
#   Invoke-WebRequest does NOT read the Windows system proxy setting.
#   So testing any overseas endpoint requires an explicit -Proxy argument.
#   (git is already configured in gitconfig, unaffected by this)
#
# Note: ASCII-only on purpose. PowerShell 5.1 reads .ps1 as ANSI (GBK on
#   Chinese Windows), so non-ASCII in single-quoted strings gets mangled and
#   a stray apostrophe can terminate the string early.

param(
    [string]$Url = 'https://rag-lab-billing.3767424179.workers.dev',
    [string]$Proxy = 'http://127.0.0.1:7890'
)

$ErrorActionPreference = 'Continue'

function Test-Endpoint {
    param([string]$Label, [string]$Uri, [string]$Method = 'GET')

    $sw = [Diagnostics.Stopwatch]::StartNew()
    try {
        $r = Invoke-WebRequest -Uri $Uri -Method $Method -Proxy $Proxy `
             -UseBasicParsing -TimeoutSec 20
        $sw.Stop()
        Write-Host ("  {0,-30} {1}  {2,5}ms  {3}" -f $Label, $r.StatusCode, $sw.ElapsedMilliseconds, $r.Content)
        return $true
    } catch {
        $sw.Stop()
        Write-Host ("  {0,-30} ERR   {1,5}ms  {2}" -f $Label, $sw.ElapsedMilliseconds, $_.Exception.Message)
        return $false
    }
}

Write-Host ''
Write-Host "Worker: $Url"
Write-Host "Proxy:  $Proxy"
Write-Host ''

$key = "probe_$([DateTimeOffset]::UtcNow.ToUnixTimeSeconds())"

Write-Host '[1] KV read'
if (-not (Test-Endpoint 'GET /quota' "$Url/quota?key=$key")) {
    Write-Host ''
    Write-Host 'Diagnostics:'
    $ie = Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings'
    Write-Host ("  system proxy enabled: {0}   (0 = OFF, 1 = ON)" -f $ie.ProxyEnable)
    $listening = [bool](Get-NetTCPConnection -LocalPort 7890 -State Listen -ErrorAction SilentlyContinue)
    Write-Host ("  port 7890 listening: {0}" -f $listening)
    Write-Host '  -> If proxy is OFF, turn it on in your Clash/v2ray client.'
    exit 1
}

Write-Host ''
Write-Host '[2] KV write (incr twice, expect count 0 then 1)'
$ok1 = Test-Endpoint 'POST /quota/incr (1st)' "$Url/quota/incr?key=$key" 'POST'
$ok2 = Test-Endpoint 'POST /quota/incr (2nd)' "$Url/quota/incr?key=$key" 'POST'

Write-Host ''
Write-Host '[3] cleanup'
Test-Endpoint 'POST /quota/reset' "$Url/quota/reset?key=$key" 'POST' | Out-Null

Write-Host ''
if ($ok1 -and $ok2) {
    Write-Host 'RESULT: KV read/write OK' -ForegroundColor Green
    exit 0
} else {
    Write-Host 'RESULT: KV write FAILED' -ForegroundColor Red
    exit 1
}
