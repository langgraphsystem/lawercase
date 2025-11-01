@echo off
REM ===============================================
REM  MegaAgent Telegram Bot - Start Script
REM ===============================================

echo.
echo [1/4] Checking Python installation...
python --version
if errorlevel 1 (
    echo ERROR: Python not found! Please install Python 3.11+
    pause
    exit /b 1
)

echo.
echo [2/4] Checking current directory...
cd /d "%~dp0"
echo Current directory: %CD%

echo.
echo [3/4] Killing old bot processes...
taskkill /F /IM python.exe 2>nul
if errorlevel 1 (
    echo No old processes found - OK
) else (
    echo Old processes killed
    timeout /t 2 >nul
)

echo.
echo [4/4] Starting Telegram bot...
echo.
echo ============================================
echo Bot is starting...
echo Press Ctrl+C to stop the bot
echo Logs will appear below:
echo ============================================
echo.

python -m telegram_interface.bot

echo.
echo ============================================
echo Bot stopped
echo ============================================
pause
