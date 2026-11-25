@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

set "ROOT=%CD%"
set "VENV=%ROOT%\.venv"
set "WITH_EXTRACT=0"
set "WITH_ANDROID=1"
set "NO_PAUSE=0"

:parse_args
if "%~1"=="" goto args_done
if /I "%~1"=="--with-extract" set "WITH_EXTRACT=1"
if /I "%~1"=="--with-android" set "WITH_ANDROID=1"
if /I "%~1"=="--without-android" set "WITH_ANDROID=0"
if /I "%~1"=="--no-pause" set "NO_PAUSE=1"
shift
goto parse_args
:args_done

echo ============================================================
echo  Gf1_AccountEval build environment
echo ============================================================
echo  Project: %ROOT%
echo.

call :detect_python
if not defined PYEXE (
  echo [INFO] Python 3.10+ was not found.
  where winget >nul 2>&1
  if errorlevel 1 goto manual_python
  echo.
  echo        This installer can install Python 3.12 automatically
  echo        via winget. Press Y to continue, N to open the download page.
  choice /C YN /T 15 /D Y /M "Install Python 3.12 now"
  if errorlevel 2 goto manual_python
  echo.
  echo [INFO] Installing Python 3.12 ...
  winget install --id Python.Python.3.12 -e --source winget --accept-package-agreements --accept-source-agreements
  call :detect_python
  if not defined PYEXE (
    echo [WARN] Python was installed but is not on PATH yet.
    echo        Close this window and run build.bat again.
    goto fail
  )
)
if not defined PYEXE goto manual_python

echo [1/4] Python: %PYEXE%
if not exist "%VENV%\Scripts\python.exe" (
  echo [2/4] Creating .venv ...
  "%PYEXE%" -m venv "%VENV%"
  if errorlevel 1 goto fail
) else (
  echo [2/4] Reusing existing .venv
)

set "PY=%VENV%\Scripts\python.exe"
echo [3/4] Installing dependencies ...
"%PY%" -m pip install --upgrade pip setuptools wheel
if errorlevel 1 goto fail
"%PY%" -m pip install -r "%ROOT%\requirements\base.txt"
if errorlevel 1 goto fail
if "%WITH_EXTRACT%"=="1" (
  echo      Installing optional UnityPy extraction dependencies ...
  "%PY%" -m pip install -r "%ROOT%\requirements\extract.txt"
  if errorlevel 1 goto fail
)
if "%WITH_ANDROID%"=="1" (
  echo      Installing Android capture dependencies ...
  "%PY%" -m pip install -r "%ROOT%\requirements\android.txt"
  if errorlevel 1 goto fail
) else (
  echo      Android capture dependencies skipped by --without-android
)

echo [4/4] Running tests ...
"%PY%" -m unittest discover -s "%ROOT%\tests" -q
if errorlevel 1 goto fail

echo.
echo ============================================================
echo  Build environment is ready.
echo    Desktop:  run.bat
echo    Tests:    .venv\Scripts\python.exe -m unittest discover -s tests -v
echo ============================================================
if "%NO_PAUSE%"=="0" pause
exit /b 0

:detect_python
set "PYEXE="
if exist "%VENV%\Scripts\python.exe" (
  set "PYEXE=%VENV%\Scripts\python.exe"
  exit /b 0
)
where py >nul 2>&1
if not errorlevel 1 (
  for /f "usebackq delims=" %%P in (`py -3.12 -c "import sys; print(sys.executable)" 2^>nul`) do set "PYEXE=%%P"
  if defined PYEXE exit /b 0
  for /f "usebackq delims=" %%P in (`py -3 -c "import sys; print(sys.executable)" 2^>nul`) do set "PYEXE=%%P"
  if defined PYEXE exit /b 0
)
where python >nul 2>&1
if not errorlevel 1 (
  for /f "usebackq delims=" %%P in (`python -c "import sys; print(sys.executable)" 2^>nul`) do set "PYEXE=%%P"
  if defined PYEXE exit /b 0
)
rem winget may install Python outside the current PATH.
for %%P in (
  "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
  "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
  "%PROGRAMFILES%\Python312\python.exe"
  "%PROGRAMFILES%\Python311\python.exe"
  "C:\Python312\python.exe"
  "C:\Python311\python.exe"
) do (
  if exist "%%~P" (
    set "PYEXE=%%~P"
    exit /b 0
  )
)
exit /b 0

:manual_python
echo.
echo [ERROR] Python 3.10+ is required.
echo         Install Python 3.12 x64 from:
echo         https://www.python.org/downloads/windows/
echo         Enable "Add Python to PATH", then run build.bat again.
start "" "https://www.python.org/downloads/windows/"
goto fail

:fail
echo.
echo [ERROR] Build failed. Read the message above.
if "%NO_PAUSE%"=="0" pause
exit /b 1
