@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

set "PY_CMD="

if exist "%~dp0.venv\Scripts\python.exe" (
  set "PY_CMD=%~dp0.venv\Scripts\python.exe"
) else (
  where py >nul 2>nul
  if %errorlevel%==0 (
    set "PY_CMD=py -3"
  ) else (
    where python >nul 2>nul
    if %errorlevel%==0 (
      set "PY_CMD=python"
    )
  )
)

if "%PY_CMD%"=="" (
  echo [ERROR] Python not found. Try creating Server\.venv first, or install Python 3 and add it to PATH.
  exit /b 1
)

echo [INFO] Running schema sync...
%PY_CMD% tools\sync_tshock_schema.py
if %errorlevel% neq 0 (
  echo [ERROR] Sync failed.
  exit /b %errorlevel%
)

echo [OK] Schema sync completed.
exit /b 0
