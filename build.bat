@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

set "ROOT=%CD%"
set "VENV=%ROOT%\.venv"
set "WITH_EXTRACT=0"
set "NO_PAUSE=0"

:parse_args
if "%~1"=="" goto args_done
if /I "%~1"=="--with-extract" set "WITH_EXTRACT=1"
if /I "%~1"=="--no-pause" set "NO_PAUSE=1"
shift
goto parse_args
:args_done

echo ============================================================
echo  Gf1_AccountEval build environment
echo ============================================================
echo  Project: %ROOT%
echo.

set "PYEXE="
if exist "%VENV%\Scripts\python.exe" (
  set "PYEXE=%VENV%\Scripts\python.exe"
  goto python_found
)

where py >nul 2>&1
if not errorlevel 1 (
  py -3.12 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
  if not errorlevel 1 (
    set "PYEXE=py -3.12"
    goto python_found
  )
  py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
  if not errorlevel 1 (
    set "PYEXE=py -3"
    goto python_found
  )
)

where python >nul 2>&1
if not errorlevel 1 (
  python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
  if not errorlevel 1 (
    set "PYEXE=python"
    goto python_found
  )
)

echo [ERROR] Python 3.10+ not found.
echo         Install Python 3.12 x64 from https://www.python.org/downloads/
echo         and enable "Add Python to PATH".
exit /b 1

:python_found
echo [1/4] Python: %PYEXE%
if not exist "%VENV%\Scripts\python.exe" (
  echo [2/4] Creating .venv ...
  %PYEXE% -m venv "%VENV%"
  if errorlevel 1 (
    echo [ERROR] Failed to create .venv
    exit /b 1
  )
) else (
  echo [2/4] Reusing existing .venv
)

set "PY=%VENV%\Scripts\python.exe"
echo [3/4] Installing dependencies ...
"%PY%" -m pip install --upgrade pip setuptools wheel
if errorlevel 1 exit /b 1
"%PY%" -m pip install -r "%ROOT%\requirements.txt"
if errorlevel 1 exit /b 1
if "%WITH_EXTRACT%"=="1" (
  echo      Installing optional UnityPy extraction dependencies ...
  "%PY%" -m pip install -r "%ROOT%\requirements-extract.txt"
  if errorlevel 1 exit /b 1
)

echo [4/4] Running tests and building PWA data ...
"%PY%" -m unittest discover -s "%ROOT%\tests" -q
if errorlevel 1 (
  echo [ERROR] Tests failed.
  exit /b 1
)
"%PY%" "%ROOT%\tools\build_web.py"
if errorlevel 1 (
  echo [ERROR] PWA build failed.
  exit /b 1
)

echo.
echo ============================================================
echo  Build environment is ready.
echo    Desktop:  run.ps1
echo    PWA:      run_web.ps1  (http://127.0.0.1:8770/)
echo    Tests:    .venv\Scripts\python.exe -m unittest discover -s tests -v
echo ============================================================
if "%NO_PAUSE%"=="0" pause
endlocal
