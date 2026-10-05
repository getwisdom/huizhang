@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
"C:\Users\leafr\ComfyUI\.venv\Scripts\python.exe" detex.py --src µ×Í¼ --strength ÖÐ --preview
pause
