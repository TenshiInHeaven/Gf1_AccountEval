# GF Account Forge WebUI / PWA launcher.
# Serves web/ locally; visit http://127.0.0.1:8770/ (installable on localhost).
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONUTF8 = "1"

$venv = Join-Path $PSScriptRoot ".venv"
$python = Join-Path $venv "Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    $base = (Get-Command python -ErrorAction Stop).Source
    Write-Host "Creating .venv ..." -ForegroundColor Cyan
    & $base -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw "venv creation failed" }
}

$check = & $python -c "import PIL; print('ok')" 2>$null
if ($check -ne "ok") {
    Write-Host "Installing web dependencies ..." -ForegroundColor Cyan
    & $python -m pip install -r (Join-Path $PSScriptRoot "requirements\web.txt")
    if ($LASTEXITCODE -ne 0) { throw "web dependency installation failed" }
}

# Rebuild the static PWA data if it has not been generated yet.
if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot "web\data\guihai_weapons.json"))) {
    Write-Host "Building web data ..." -ForegroundColor Cyan
    & $python (Join-Path $PSScriptRoot "tools\build_web.py")
    if ($LASTEXITCODE -ne 0) { throw "build_web failed" }
}

& $python (Join-Path $PSScriptRoot "web\serve.py") --open @args
exit $LASTEXITCODE
