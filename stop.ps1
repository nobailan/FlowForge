# FlowForge v0.5 - Stop All Services
Write-Host "=== FlowForge Stop ===" -ForegroundColor Yellow

$python = "E:\anaconda3\envs\graph\python.exe"
$backendDir = Join-Path $PSScriptRoot "backend"

# 1. Clean running executions + OpenCode sessions
Write-Host "[Clean] Clearing stuck executions..." -ForegroundColor Cyan
& $python "$backendDir\cleanup.py" 2>&1 | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }

# 2. Kill processes on known ports (6379=Redis, 8000=Backend, 5173=Vite, 4096=OpenCode)
foreach ($port in @(8000, 5173, 4096, 6379)) {
    $conn = netstat -ano | Select-String ":$port" | Select-String "LISTENING"
    if ($conn) {
        $procIds = ($conn | ForEach-Object { ($_ -split '\s+')[-1] } | Sort-Object -Unique)
        foreach ($procId in $procIds) {
            Write-Host "[$port] Stopping PID $procId"
            taskkill /F /PID $procId 2>$null
        }
    } else {
        Write-Host "[$port] Free"
    }
}

if ($args[0] -eq "--all") {
    Write-Host "[--all] Killing all Python + Node + Bun..."
    taskkill /F /IM python.exe 2>$null
    taskkill /F /IM node.exe 2>$null
    taskkill /F /IM bun.exe 2>$null
}

Write-Host "Done." -ForegroundColor Green
