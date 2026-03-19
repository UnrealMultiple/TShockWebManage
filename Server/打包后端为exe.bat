@echo off
setlocal

cd /d %~dp0

echo [Build] Packaging backend to exe...

if not exist ".venv\Scripts\python.exe" (
  set "BOOTSTRAP_PY="
  where py >nul 2>nul
  if %errorlevel%==0 (
    set "BOOTSTRAP_PY=py -3"
  ) else (
    where python >nul 2>nul
    if %errorlevel%==0 set "BOOTSTRAP_PY=python"
  )

  if "%BOOTSTRAP_PY%"=="" (
    echo [Error] Python not found on this machine.
    echo [Hint] Install Python 3.10+ on a dev machine, then run this script again.
    pause
    exit /b 1
  )

  echo [Build] Creating .venv...
  %BOOTSTRAP_PY% -m venv .venv
  if %errorlevel% neq 0 (
    echo [Error] Failed to create virtual environment.
    pause
    exit /b 1
  )
)

set "PY=.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo [Error] Venv python missing: %PY%
  pause
  exit /b 1
)

%PY% -m pip --version >nul 2>nul
if %errorlevel% neq 0 (
  echo [Build] pip not found in venv, trying ensurepip...
  %PY% -m ensurepip --upgrade >nul 2>nul
)

%PY% -m pip --version >nul 2>nul
if %errorlevel% neq 0 (
  echo [Error] pip unavailable in venv.
  pause
  exit /b 1
)

echo [Build] Installing dependencies and PyInstaller...
%PY% -m pip install --upgrade pip
if %errorlevel% neq 0 (
  echo [Error] pip upgrade failed.
  pause
  exit /b 1
)

%PY% -m pip install -r requirements.txt pyinstaller
if %errorlevel% neq 0 (
  echo [Error] Failed to install requirements/pyinstaller.
  pause
  exit /b 1
)

echo [Build] Running PyInstaller...
%PY% -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --name terraria-backend ^
  --distpath . ^
  --workpath build ^
  --specpath . ^
  --collect-all fastapi ^
  --collect-all starlette ^
  --collect-all pydantic ^
  --collect-all uvicorn ^
  run_backend.py

if %errorlevel% neq 0 (
  echo [Error] Packaging failed.
  pause
  exit /b 1
)

echo [Done] Output: %cd%\terraria-backend.exe
pause