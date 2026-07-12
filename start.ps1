# FlowForge v0.7 - Start All Services
$python = "E:\anaconda3\envs\graph\python.exe"
$opencodeDir = "E:\agentProject\opencode"
$redisDir = "E:\redis"
$root = $PSScriptRoot
$pidFile = Join-Path $root ".flowforge_pids.txt"
Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
$pids = @()

if (-not (Test-Path $python)) {
    Write-Host "[ERROR] Python not found: $python" -ForegroundColor Red
    return
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  FlowForge v0.7" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# 0. 强制清理旧进程（防止旧代码占端口导致新代码起不来）
Write-Host "[Pre-clean] Killing any existing services..." -ForegroundColor DarkGray
foreach ($port in @(8000, 5173, 4096, 6379)) {
    $conn = netstat -ano | Select-String ":$port" | Select-String "LISTENING"
    if ($conn) {
        $oldPids = ($conn | ForEach-Object { ($_ -split '\s+')[-1] } | Sort-Object -Unique)
        foreach ($oldPid in $oldPids) {
            taskkill /F /T /PID $oldPid 2>$null
            Write-Host "  Killed PID $oldPid on port $port" -ForegroundColor Gray
        }
    }
}
Start-Sleep 2

# 2. Redis
$redisRunning = netstat -ano | Select-String ":6379" | Select-String "LISTENING"
if (-not $redisRunning) {
    Write-Host "[Redis] Starting on localhost:6379 ..." -ForegroundColor Red
    $p = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$redisDir'; Write-Host 'Redis Server' -ForegroundColor Red; .\redis-server.exe redis.windows.conf" -PassThru
    $pids += $p.Id
    Start-Sleep 2
} else {
    Write-Host "[Redis] Already running on :6379" -ForegroundColor Green
}

# 3. OpenCode Server
Write-Host "[OpenCode] Starting on http://localhost:4096 ..." -ForegroundColor Magenta
$p = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$opencodeDir'; Write-Host 'OpenCode Server' -ForegroundColor Magenta; bun run --cwd packages/opencode src/index.ts serve --port 4096" -PassThru
$pids += $p.Id
Start-Sleep 2

# 4. FlowForge Backend
Write-Host "[Backend] Starting on http://localhost:8000 ..." -ForegroundColor Yellow
$p = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\backend'; Write-Host 'FlowForge Backend' -ForegroundColor Cyan; & '$python' run.py" -PassThru
$pids += $p.Id
Start-Sleep 1

# 5. FlowForge Frontend
Write-Host "[Frontend] Starting on http://localhost:5173 ..." -ForegroundColor Yellow
$p = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; Write-Host 'FlowForge Frontend' -ForegroundColor Cyan; npm run dev" -PassThru
$pids += $p.Id

# 保存 PID 到文件，供 stop.ps1 读取
$pids | Out-File -FilePath $pidFile -Encoding utf8

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
