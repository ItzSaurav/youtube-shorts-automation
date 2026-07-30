@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"
echo [INFO] Starting YouTube Automation Pipeline

if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)

for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set LOG_DATE=%datetime:~0,8%
set LOGFILE=logs\scheduler_%LOG_DATE%.log

echo [INFO] Running scheduler... >> "%LOGFILE%"
python src\scheduler.py --now >> "%LOGFILE%" 2>&1

echo [INFO] Cleaning up logs older than 7 days... >> "%LOGFILE%"
forfiles /p logs /m *.log /d -7 /c "cmd /c del @path" >> "%LOGFILE%" 2>&1
echo [INFO] Done. >> "%LOGFILE%"
endlocal
