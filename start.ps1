# FlowForge v0.2 - Start All Services
$python = "E:\anaconda3\envs\graph\python.exe"
$opencodeDir = "E:\agentProject\opencode"
$root = $PSScriptRoot

if (-not (Test-Path $python)) {
    Write-Host "[ERROR] Python not found: $python" -ForegroundColor Red
    return
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  FlowForge v0.2" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# 1. OpenCode Server
Write-Host "[OpenCode] Starting on http://localhost:4096 ..." -ForegroundColor Magenta
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$opencodeDir'; Write-Host 'OpenCode Server' -ForegroundColor Magenta; bun run --cwd packages/opencode src/index.ts serve --port 4096"
Start-Sleep 2

# 2. FlowForge Backend
Write-Host "[Backend] Starting on http://localhost:8000 ..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\backend'; Write-Host 'FlowForge Backend' -ForegroundColor Cyan; & '$python' run.py"
Start-Sleep 1

# 3. FlowForge Frontend
Write-Host "[Frontend] Starting on http://localhost:5173 ..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; Write-Host 'FlowForge Frontend' -ForegroundColor Cyan; npm run dev"

Start-Sleep 5

# 验证
Write-Host ""
try {
    $h = Invoke-RestMethod "http://localhost:8000/api/health" -TimeoutSec 3
    Write-Host "[Backend]  OK - $($h.node_types.Count) node types" -ForegroundColor Green
} catch { Write-Host "[Backend]  starting..." -ForegroundColor DarkYellow }

try {
    Invoke-RestMethod "http://localhost:4096" -TimeoutSec 3 | Out-Null
    Write-Host "[OpenCode] OK" -ForegroundColor Green
} catch { Write-Host "[OpenCode] starting..." -ForegroundColor DarkYellow }

try {
    Invoke-RestMethod "http://localhost:5173" -TimeoutSec 3 | Out-Null
    Write-Host "[Frontend] OK" -ForegroundColor Green
} catch { Write-Host "[Frontend] starting..." -ForegroundColor DarkYellow }

Write-Host ""
Write-Host "Browser -> http://localhost:5173" -ForegroundColor White
Write-Host "Stop   -> .\stop.ps1" -ForegroundColor Gray
Write-Host ""
