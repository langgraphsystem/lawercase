@echo off
REM Quick Smoke Test Runner for Windows
REM Tests full case cycle in ~2 minutes

echo ======================================
echo   Quick Smoke Test - Full Case Cycle
echo ======================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python not found. Please install Python 3.11+
    exit /b 1
)

REM Check if pytest is installed
python -c "import pytest" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Installing pytest...
    pip install pytest pytest-asyncio
)

echo Running smoke tests...
echo.

REM Run smoke tests
pytest tests\smoke\test_quick_cycle.py -v -s --tb=short

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ======================================
    echo   SMOKE TEST PASSED
    echo ======================================
) else (
    echo.
    echo ======================================
    echo   SMOKE TEST FAILED
    echo ======================================
    exit /b 1
)

pause
