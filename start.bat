@echo off
cd /d "%~dp0"
title TalentNet Local
start "TalentNet Local" powershell.exe -NoProfile -ExecutionPolicy Bypass -NoExit -File "%~dp0start.ps1" -OpenBrowser
exit /b 0
