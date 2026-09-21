@echo off
echo =================================================================
echo Starting KnoQuest Enterprise Knowledge Agent Backend...
echo =================================================================
cd /d "%~dp0"
py -3.12 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pause
