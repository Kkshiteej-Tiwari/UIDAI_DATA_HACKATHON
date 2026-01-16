@echo off
echo ================================================================
echo Starting UIDAI Datathon Application
echo ================================================================
echo.
echo Starting all servers:
echo   - Frontend (Vite)     : http://localhost:8080
echo   - Express Backend     : http://localhost:3001
echo   - ML Backend (FastAPI): http://localhost:8000
echo.
echo Press Ctrl+C to stop all servers
echo ================================================================
echo.

npm run dev:all
