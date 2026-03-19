@echo off
setlocal

where py >nul 2>nul
if %errorlevel%==0 (
	py -3 launcher.py
	goto :end
)

where python >nul 2>nul
if %errorlevel%==0 (
	python launcher.py
	goto :end
)

echo [提示] 未检测到 Python，改用纯 bat 回退启动流程。
start "代理端" cmd /c "cd /d Agent\bin\TShock && start.bat"
start "后端" cmd /c "cd /d Server && 启动后端.bat"

where npm >nul 2>nul
if %errorlevel%==0 (
	start "网页端" cmd /c "cd /d Web && npm run dev"
) else (
	echo [警告] 未检测到 npm，网页端未启动。
)

:end
pause