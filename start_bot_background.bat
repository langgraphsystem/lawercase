@echo off
REM ===============================================
REM  MegaAgent Telegram Bot - Background Start
REM ===============================================

echo.
echo [1/3] Killing old bot processes...
taskkill /F /IM python.exe 2>nul
timeout /t 1 >nul

echo.
echo [2/3] Starting bot in background...
cd /d "%~dp0"

start /B python -m telegram_interface.bot > bot_background.log 2>&1

echo.
echo [3/3] Waiting 3 seconds for startup...
timeout /t 3 >nul

echo.
echo ============================================
echo Bot started in background!
echo.
echo To see logs:    type bot_background.log
echo To stop bot:    taskkill /F /IM python.exe
echo ============================================
echo.

REM Show first 20 lines of log
echo Initial logs:
echo --------------------------------------------
powershell -Command "Get-Content bot_background.log -Tail 20"
echo.

pause
