@echo off
REM ============================================================================
REM Document Monitor - Quick Start Script
REM ============================================================================

echo.
echo ========================================================================
echo  MEGA AGENT PRO - Document Generation Monitor
echo ========================================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.11+ from https://www.python.org/
    pause
    exit /b 1
)

echo [INFO] Python found:
python --version
echo.

REM Check if uvicorn is installed
python -c "import uvicorn" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] uvicorn not found. Installing...
    pip install uvicorn
    echo.
)

REM Check if FastAPI is installed
python -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] FastAPI not found. Installing...
    pip install fastapi
    echo.
)

echo ========================================================================
echo  Starting FastAPI Server...
echo ========================================================================
echo.
echo  Development server with hot-reload enabled
echo  API endpoints: http://localhost:8000/api/*
echo  Web interface: http://localhost:8000/index.html
echo  API docs: http://localhost:8000/docs
echo.
echo  Press Ctrl+C to stop the server
echo ========================================================================
echo.

REM Start the server
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

pause
