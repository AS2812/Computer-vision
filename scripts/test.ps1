$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot "common.ps1")
Push-Location $Root
try {
    Invoke-Checked { uv sync --project services/api --extra dev --extra onnx } "Python environment sync"
    Invoke-Checked { uv run --project services/api pytest services/api/tests } "Backend tests"
    $env:PYTHONPATH = (Join-Path $Root "ml/training")
    Invoke-Checked { uv run --project services/api pytest ml/training/test_evaluate.py --no-cov } "Model release-gate tests"
    Invoke-Checked { uv run --project services/api python scripts/model_audit.py } "Installed model metadata audit"
    Invoke-Checked { uv run --project services/api python scripts/benchmark_model.py --runs 3 --check } "CPU and memory benchmark"
    Invoke-Checked { pnpm --filter @agrovision/web test } "Frontend unit tests"
    Invoke-Checked { pnpm --filter @agrovision/web build } "Frontend production build"
    Invoke-Checked { pnpm --filter @agrovision/web test:e2e } "Browser end-to-end tests"

    if (Test-DockerRunning) {
        Invoke-Checked { pnpm dlx supabase start } "Supabase start"
        Invoke-Checked { pnpm dlx supabase db test } "Supabase pgTAP tests"
    } else {
        Write-Warning "Docker Desktop is not running. pgTAP tests were skipped."
    }
} finally {
    Pop-Location
}
