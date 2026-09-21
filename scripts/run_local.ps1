# run_local.ps1 — 一键跑 RAG demo (Windows)
#
# 用法:
#   1. 第一次跑会自动创建 venv + 装依赖（慢，约 2 分钟）
#   2. 编辑 .env 填 DEEPSEEK_API_KEY + ZHIPU_API_KEY
#   3. 之后每次跑直接执行本脚本

$ErrorActionPreference = "Stop"

# 切到仓库根（脚本在 scripts/ 里）
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
Set-Location $RepoRoot

Write-Host "[INFO] 工作目录: $RepoRoot" -ForegroundColor Cyan
Write-Host ""

# --- 1. 配清华 pip 镜像（仅首次，之后跳过） ---
$pipConfig = "$env:APPDATA\pip\pip.ini"
if (-not (Test-Path $pipConfig)) {
    Write-Host "[INFO] 配清华 pip 镜像..." -ForegroundColor Yellow
    pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
    pip config set global.trusted-host pypi.tuna.tsinghua.edu.cn
}

# --- 2. 检查 + 建虚拟环境 ---
if (-not (Test-Path ".venv")) {
    Write-Host "[INFO] 创建虚拟环境 .venv ..." -ForegroundColor Yellow
    python -m venv .venv
}

# --- 3. 激活 venv ---
$activateScript = ".\.venv\Scripts\Activate.ps1"
if (Test-Path $activateScript) {
    & $activateScript
} else {
    Write-Host "[ERROR] 找不到 $activateScript" -ForegroundColor Red
    exit 1
}

# --- 4. 装依赖 ---
Write-Host "[INFO] 装依赖（首次约 2 分钟）..." -ForegroundColor Yellow
pip install -q -r requirements.txt

# --- 5. 检查 .env ---
if (-not (Test-Path ".env")) {
    Write-Host ""
    Write-Host "[WARN] 没找到 .env, 已复制 .env.example -> .env" -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "[WARN] 请编辑 .env 填 2 个 API key:" -ForegroundColor Yellow
    Write-Host "   - DEEPSEEK_API_KEY: https://platform.deepseek.com/" -ForegroundColor Gray
    Write-Host "   - ZHIPU_API_KEY:    https://bigmodel.cn/" -ForegroundColor Gray
    Write-Host ""
    notepad .env
}

# --- 6. 检查 data/raw/ ---
if (-not (Test-Path "data\raw") -or -not (Get-ChildItem "data\raw" -ErrorAction SilentlyContinue)) {
    Write-Host ""
    Write-Host "[WARN] data\raw\ 是空的, 放几个 .txt 文件进去" -ForegroundColor Yellow
}

# --- 7. 跑 demo ---
Write-Host ""
Write-Host "[INFO] 启动 RAG demo ..." -ForegroundColor Green
Write-Host ""
python src\minimal_rag.py