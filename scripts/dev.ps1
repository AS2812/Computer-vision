$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot "common.ps1")

if (Test-DockerRunning) {
    Push-Location $Root
    try {
        try { pnpm dlx supabase start *> $null } catch {
            Write-Warning "Supabase start reported an error; continuing with the local API fallback."
        }
    } finally {
        Pop-Location
    }
}

$UvCommand = (Get-Command uv.exe).Source
$PnpmCommand = (Get-Command pnpm.cmd).Source
Stop-AgroVisionApiProcesses -Port 8765
Start-Process -FilePath $UvCommand -ArgumentList @("run", "--project", "services/api", "uvicorn", "app.main:app", "--app-dir", "services/api", "--host", "127.0.0.1", "--port", "8765", "--reload") -WorkingDirectory $Root -WindowStyle Hidden
Wait-AgroVisionApi -Url "http://127.0.0.1:8765"

$dashboardListeners = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue
foreach ($listener in $dashboardListeners) {
    Stop-Process -Id $listener.OwningProcess -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Milliseconds 400
Start-Process -FilePath $PnpmCommand -ArgumentList @("--filter", "@agrovision/web", "dev") -WorkingDirectory $Root -WindowStyle Hidden

$dashboardDeadline = (Get-Date).AddSeconds(20)
while ((Get-Date) -lt $dashboardDeadline) {
    try {
        $dashboard = Invoke-WebRequest "http://127.0.0.1:5173" -UseBasicParsing -TimeoutSec 3
        if ($dashboard.StatusCode -eq 200) {
            break
        }
    } catch {
        Start-Sleep -Milliseconds 400
    }
}
if (-not (Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue)) {
    throw "AgroVision dashboard did not start on port 5173."
}

Write-Host "AgroVision started:"
Write-Host "  Dashboard: http://localhost:5173"
Write-Host "  API docs:  http://127.0.0.1:8765/docs"
Write-Host "  Supabase:  http://127.0.0.1:54323 (when Docker is running)"
