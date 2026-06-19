param(
  [Parameter(Mandatory = $true)]
  [string] $SupabaseProjectRef,

  [Parameter(Mandatory = $true)]
  [string] $SupabaseAnonKey,

  [Parameter(Mandatory = $true)]
  [string] $SupabaseAccessToken,

  [Parameter(Mandatory = $true)]
  [string] $SupabaseDbPassword,

  [Parameter(Mandatory = $true)]
  [string] $ExternalLlmApiKey,

  [string] $NetlifyAuthToken = $env:NETLIFY_AUTH_TOKEN,
  [string] $NetlifySiteId = $env:NETLIFY_SITE_ID
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$env:SUPABASE_ACCESS_TOKEN = $SupabaseAccessToken
$supabaseUrl = "https://$SupabaseProjectRef.supabase.co"

Write-Host "Installing dependencies..." -ForegroundColor Cyan
pnpm install --frozen-lockfile

Write-Host "Applying Supabase migrations..." -ForegroundColor Cyan
npx --yes supabase@latest link --project-ref $SupabaseProjectRef --password $SupabaseDbPassword
npx --yes supabase@latest db push --linked --include-all --password $SupabaseDbPassword

Write-Host "Deploying Supabase Edge Functions..." -ForegroundColor Cyan
npx --yes supabase@latest functions deploy analyze --project-ref $SupabaseProjectRef
npx --yes supabase@latest functions deploy assistant --project-ref $SupabaseProjectRef

Write-Host "Setting Supabase Edge Function secrets..." -ForegroundColor Cyan
npx --yes supabase@latest secrets set --project-ref $SupabaseProjectRef `
  EXTERNAL_LLM_API_URL="https://opencode.ai/zen/v1/chat/completions" `
  EXTERNAL_LLM_API_KEY="$ExternalLlmApiKey" `
  EXTERNAL_LLM_MODEL="deepseek-v4-flash-free" `
  EXTERNAL_VISION_MODEL="mimo-v2.5-free" `
  EXTERNAL_LLM_MAX_TOKENS="2000" `
  EXTERNAL_LLM_REASONING_EFFORT="low"

Write-Host "Building web app..." -ForegroundColor Cyan
$env:VITE_SUPABASE_URL = $supabaseUrl
$env:VITE_SUPABASE_ANON_KEY = $SupabaseAnonKey
pnpm --filter "@agrovision/web" build

if ($NetlifyAuthToken -and $NetlifySiteId) {
  Write-Host "Deploying to Netlify production..." -ForegroundColor Cyan
  $env:NETLIFY_AUTH_TOKEN = $NetlifyAuthToken
  npx --yes netlify-cli@latest env:set VITE_SUPABASE_URL $supabaseUrl --site $NetlifySiteId
  npx --yes netlify-cli@latest env:set VITE_SUPABASE_ANON_KEY $SupabaseAnonKey --site $NetlifySiteId
  npx --yes netlify-cli@latest deploy --prod --dir "apps/web/dist" --site $NetlifySiteId
} else {
  Write-Host "Netlify deploy skipped. Set NETLIFY_AUTH_TOKEN and NETLIFY_SITE_ID to deploy automatically." -ForegroundColor Yellow
  Write-Host "Built files are ready in apps/web/dist"
}

Write-Host "Done." -ForegroundColor Green
