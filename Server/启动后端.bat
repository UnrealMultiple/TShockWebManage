@echo off
setlocal

cd /d "%~dp0"

set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" (
	echo [ERROR] 未找到虚拟环境解释器: %PYTHON_EXE%
	echo [HINT] 请先在 Server 目录创建 .venv 并安装依赖。
	exit /b 1
)

"%PYTHON_EXE%" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 7773
exit /b %errorlevel%