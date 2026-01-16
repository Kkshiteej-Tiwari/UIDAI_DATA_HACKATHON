@echo off
REM Start Operations Monitoring Backend

cd /d "%~dp0"

REM Check if virtual environment exists
if not exist "..\..\\.venv" (
    echo Error: Virtual environment not found at ..\..\\.venv
    exit /b 1
)

REM Start server using virtual environment Python
echo Starting Operations Monitoring Backend on port 8001...
"..\..\\.venv\Scripts\python.exe" -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
