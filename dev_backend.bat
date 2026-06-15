@echo off
setlocal

cd /d "%~dp0backend"

if not exist ".venv\Scripts\python.exe" (
  echo Creating backend virtual environment...
  python -m venv .venv
  if errorlevel 1 exit /b 1
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 exit /b 1

echo Installing backend requirements...
python -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

echo Starting backend at http://127.0.0.1:8001
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001

endlocal
