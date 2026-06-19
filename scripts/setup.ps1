$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot "common.ps1")

if (-not (Test-Path (Join-Path $Root ".env"))) {
    Copy-Item -LiteralPath (Join-Path $Root ".env.example") -Destination (Join-Path $Root ".env")
}

Push-Location $Root
try {
    Invoke-Checked { pnpm install } "pnpm install"
    Invoke-Checked { pnpm --filter @agrovision/web exec playwright install chromium } "Playwright browser install"
    Invoke-Checked { uv sync --project services/api --extra dev --extra onnx } "Python environment sync"
    Invoke-Checked { uv run --project services/api python scripts/download_models.py } "Model download verification"

    if (Test-DockerRunning) {
        Invoke-Checked { pnpm dlx supabase start } "Supabase start"
        Invoke-Checked { pnpm dlx supabase db reset } "Supabase database reset"
        Invoke-Checked { uv run --project services/api python scripts/configure_local_supabase.py } "Supabase local environment configuration"
        Invoke-Checked { uv run --project services/api python scripts/seed_local_demo.py } "Supabase demo data seed"
    } else {
        Write-Warning "Docker Desktop is not running. Supabase setup was skipped; the API fallback still works."
    }
} finally {
    Pop-Location
}
