@echo off
chcp 65001 > nul
cd /d "%~dp0..\frontend"
set "NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8015"
call npm.cmd run build
if errorlevel 1 exit /b %errorlevel%
call npm.cmd run start -- -p 3025
