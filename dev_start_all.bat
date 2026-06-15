@echo off
setlocal

start "Asset Manager Backend" cmd /k "%~dp0dev_backend.bat"
start "Asset Manager Frontend" cmd /k "%~dp0dev_frontend.bat"

echo Backend:  http://127.0.0.1:8001
echo Frontend: http://127.0.0.1:5173/

endlocal
