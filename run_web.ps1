# GF Account Forge WebUI / PWA launcher.
# Serves web/ locally; visit http://127.0.0.1:8770/ (installable on localhost).
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONUTF8 = "1"

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    $python = (Get-Command python -ErrorAction Stop).Source
}

# Rebuild the static PWA data if it has not been generated yet.
if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot "web\data\guihai_weapons.json"))) {
    Write-Host "Building web data ..." -ForegroundColor Cyan
    & $python (Join-Path $PSScriptRoot "tools\build_web.py")
    if ($LASTEXITCODE -ne 0) { throw "build_web failed" }
}

& $python (Join-Path $PSScriptRoot "web\serve.py") --open @args
exit $LASTEXITCODE
