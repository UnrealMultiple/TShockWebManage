@echo off
setlocal

cd /d %~dp0

echo [Build] Packaging backend to exe...

set "RELEASE_DIR=package\backend"
set "PYI_DIST_DIR=build\dist"
set "PYI_WORK_DIR=build\pyinstaller"
set "PYI_SPEC_DIR=build"

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
  --distpath "%PYI_DIST_DIR%" ^
  --workpath "%PYI_WORK_DIR%" ^
  --specpath "%PYI_SPEC_DIR%" ^
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

if not exist "%PYI_DIST_DIR%\terraria-backend.exe" (
  echo [Error] EXE not found after build: %PYI_DIST_DIR%\terraria-backend.exe
  pause
  exit /b 1
)

if exist "%RELEASE_DIR%" rmdir /s /q "%RELEASE_DIR%"
mkdir "%RELEASE_DIR%"

copy /y "%PYI_DIST_DIR%\terraria-backend.exe" "%RELEASE_DIR%\terraria-backend.exe" >nul
if %errorlevel% neq 0 (
  echo [Error] Failed to copy exe to release directory.
  pause
  exit /b 1
)

if exist "%PYI_DIST_DIR%" rmdir /s /q "%PYI_DIST_DIR%"
if exist "%PYI_WORK_DIR%" rmdir /s /q "%PYI_WORK_DIR%"
if exist "%PYI_SPEC_DIR%\terraria-backend.spec" del /q "%PYI_SPEC_DIR%\terraria-backend.spec"
if exist "terraria-backend.spec" del /q "terraria-backend.spec"
if exist "terraria-backend.exe" del /q "terraria-backend.exe"

echo [Done] Output: %cd%\%RELEASE_DIR%\terraria-backend.exe
pause