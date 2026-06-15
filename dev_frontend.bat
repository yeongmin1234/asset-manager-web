@echo off
setlocal

cd /d "%~dp0frontend"

if not exist "node_modules" (
  echo Installing frontend dependencies...
  npm install
  if errorlevel 1 exit /b 1
)

echo Starting frontend at http://127.0.0.1:5173/
npm run dev

endlocal
