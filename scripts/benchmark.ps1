$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Push-Location $Root
try {
    uv run --project services/api python scripts/benchmark_model.py --runs 10 --check --output ml/models/benchmark.latest.json
    if ($LASTEXITCODE -ne 0) {
        throw "Benchmark acceptance limits failed."
    }
} finally {
    Pop-Location
}
