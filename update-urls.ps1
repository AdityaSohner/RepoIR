# =============================================================
# RepoIR - Cloudflare URL Updater
# Usage: .\update-urls.ps1 -backend "https://xxxx.trycloudflare.com" -frontend "https://yyyy.trycloudflare.com"
# If you only have one tunnel (backend), omit -frontend
# =============================================================

param(
    [Parameter(Mandatory=$true)]
    [string]$backend,

    [Parameter(Mandatory=$false)]
    [string]$frontend = ""
)

$ROOT = $PSScriptRoot
$FRONTEND_ENV = Join-Path $ROOT "Frontend\.env"

# Strip trailing slash just in case
$backend  = $backend.TrimEnd('/')
$frontend = $frontend.TrimEnd('/')

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  RepoIR - Cloudflare URL Updater" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Update Frontend/.env
if (Test-Path $FRONTEND_ENV) {
    $content = Get-Content $FRONTEND_ENV -Raw
    $content = $content -replace 'VITE_API_BASE_URL=.*', "VITE_API_BASE_URL=$backend"
    Set-Content $FRONTEND_ENV $content -NoNewline
    Write-Host "[OK] Frontend/.env updated" -ForegroundColor Green
    Write-Host "     VITE_API_BASE_URL = $backend" -ForegroundColor Gray
} else {
    Write-Host "[SKIP] Frontend/.env not found" -ForegroundColor Yellow
}

Write-Host ""

# Print Google Console instructions
Write-Host "--------------------------------------" -ForegroundColor Yellow
Write-Host " ACTION REQUIRED: Google Cloud Console" -ForegroundColor Yellow
Write-Host "--------------------------------------" -ForegroundColor Yellow
Write-Host " URL: https://console.cloud.google.com/apis/credentials" -ForegroundColor Cyan
Write-Host ""
Write-Host " Authorized JavaScript origins:" -ForegroundColor White

if ($frontend -ne "") {
    Write-Host "   $frontend" -ForegroundColor Green
} else {
    Write-Host "   $backend" -ForegroundColor Green
}

Write-Host ""
Write-Host " Authorized redirect URIs:" -ForegroundColor White

if ($frontend -ne "") {
    Write-Host "   $frontend/auth/callback" -ForegroundColor Green
    Write-Host "   $frontend/login" -ForegroundColor Green
} else {
    Write-Host "   $backend/auth/callback" -ForegroundColor Green
    Write-Host "   $backend/login" -ForegroundColor Green
}

Write-Host ""
Write-Host "--------------------------------------" -ForegroundColor Yellow
Write-Host ""

# Copy frontend URL to clipboard
$clipContent = if ($frontend -ne "") { $frontend } else { $backend }
$clipContent | Set-Clipboard
Write-Host "[INFO] URL copied to clipboard." -ForegroundColor Cyan
Write-Host ""
Write-Host "[REMINDER] Restart Vite dev server to pick up new .env:" -ForegroundColor Magenta
Write-Host "   cd Frontend && npm run dev" -ForegroundColor Gray
Write-Host ""
Write-Host "Done!" -ForegroundColor Green
