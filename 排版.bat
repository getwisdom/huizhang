@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0layout.ps1"
echo.
echo Layout done.
echo.
pause
