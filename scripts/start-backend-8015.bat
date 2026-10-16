@echo off
chcp 65001 > nul
setlocal
set "ROOT=%~dp0.."
set "PYTHON=%ROOT%\backend\.venv\Scripts\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"
cd /d "%ROOT%\backend"
"%PYTHON%" -m uvicorn app.main:app --host 127.0.0.1 --port 8015
