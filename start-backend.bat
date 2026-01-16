@echo off
echo Starting UIDAI Backend Services...
echo.

:: Start ML Backend in background
echo [1/2] Starting ML Backend (Python FastAPI) on port 8001...
start "ML Backend" cmd /c "cd /d %~dp0ml_backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8001"

:: Wait for ML backend to start
echo Waiting for ML Backend to initialize...
timeout /t 3 /nobreak > nul

:: Start Node.js Backend
echo [2/2] Starting Node.js Backend on port 3001...
cd /d %~dp0server
npm start

echo.
echo Both servers started!
echo - Node.js Backend: http://localhost:3001
echo - ML Backend: http://localhost:8001 (internal)
pause
