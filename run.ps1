# GF Account Forge launcher.
# Creates .venv on first run, installs requirements, then starts the Qt app.
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONUTF8 = "1"

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    Write-Host "Creating .venv ..." -ForegroundColor Cyan
    $base = (Get-Command python -ErrorAction Stop).Source
    & $base -m venv (Join-Path $PSScriptRoot ".venv")
    if ($LASTEXITCODE -ne 0) { throw "venv creation failed" }
}

$check = & $python -c "import PySide6, PIL; print('ok')" 2>$null
if ($check -ne "ok") {
    Write-Host "Installing dependencies ..." -ForegroundColor Cyan
    & $python -m pip install -r (Join-Path $PSScriptRoot "requirements.txt")
    if ($LASTEXITCODE -ne 0) { throw "dependency installation failed" }
}

& $python -m app.main
exit $LASTEXITCODE
