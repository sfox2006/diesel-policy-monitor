@echo off
REM ─────────────────────────────────────────────────────────────────────────────
REM run_briefing.bat
REM Called by Windows Task Scheduler.
REM Edit PROJ_DIR and VENV_DIR to match your setup.
REM ─────────────────────────────────────────────────────────────────────────────

SET PROJ_DIR=C:\Users\SamFox\OneDrive - Mandala Partners\policy-monitor
SET VENV_DIR=%PROJ_DIR%\.venv
SET LOG_FILE=%PROJ_DIR%\logs\task_scheduler.log

echo ────────────────────────────────────────── >> "%LOG_FILE%"
echo %DATE% %TIME%  Starting PolicyMonitor >> "%LOG_FILE%"

cd /d "%PROJ_DIR%"
call "%VENV_DIR%\Scripts\activate.bat"

python main.py >> "%LOG_FILE%" 2>&1

echo %DATE% %TIME%  Done >> "%LOG_FILE%"