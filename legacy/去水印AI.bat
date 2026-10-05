@echo off
cd /d "%~dp0"
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PY=C:\Users\leafr\ComfyUI\.venv\Scripts\python.exe
if not exist "%PY%" set PY=python
"%PY%" "%~dp0remove_watermark_ai.py" %*
echo.
pause

