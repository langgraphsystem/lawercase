@echo off
REM ===============================================
REM  MegaAgent Telegram Bot - Start Script (Windows)
REM ===============================================

setlocal ENABLEDELAYEDEXPANSION
cd /d %~dp0

echo.
echo [*] Working dir: %CD%

if not exist .env (
  echo [!] .env not found in this folder. The bot will fail without TELEGRAM_BOT_TOKEN.
  echo     Create .env or copy from example and set TELEGRAM_BOT_TOKEN.
)

if exist .venv\Scripts\activate.bat (
  call .venv\Scripts\activate.bat
)

if not exist logs (
  mkdir logs
)

set PYTHONUNBUFFERED=1
set PYTHONIOENCODING=utf-8

echo.
echo [*] Starting MegaAgent Telegram bot (polling)...
echo     Logs will be appended to logs\telegram_bot.log
echo.

powershell -NoLogo -NoProfile -Command ^
  "try { ^
      python -m telegram_interface.bot 2^>^&1 ^| Tee-Object -FilePath 'logs\\telegram_bot.log' -Append ^
    } catch { ^
      Write-Host '[!] Bot failed to start:' -ForegroundColor Red; ^
      Write-Host $_.Exception.Message -ForegroundColor Red; ^
      exit 1 ^
    }"

set ERR=%ERRORLEVEL%
if not %ERR%==0 (
  echo.
  echo [!] Bot exited with code %ERR%.
  echo     See logs\telegram_bot.log for details.
  pause
)

endlocal

