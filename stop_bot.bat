@echo off
REM ===============================================
REM  MegaAgent Telegram Bot - Stop Script
REM ===============================================

echo.
echo Stopping all Python/bot processes...
echo.

taskkill /F /IM python.exe 2>nul

if errorlevel 1 (
    echo No bot processes found - nothing to stop
) else (
    echo Bot processes killed successfully
)

echo.
echo Done!
pause
