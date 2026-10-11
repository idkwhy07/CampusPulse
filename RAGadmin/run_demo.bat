@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  py -3 -m venv .venv
  if errorlevel 1 goto error
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto error
echo.
echo Mo trinh duyet tai http://127.0.0.1:8001
echo Nhan Ctrl+C de dung server.
.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8001
:error
pause
