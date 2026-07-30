@echo off
setlocal

cd /d "%~dp0"
set SCRIPT_PATH=%~dp0run_youtube_automation.bat

echo [INFO] Creating scheduled tasks...
schtasks /create /tn "YouTubeAutomation_Morning" /tr "\"%SCRIPT_PATH%\"" /sc daily /st 09:00 /f
schtasks /create /tn "YouTubeAutomation_Afternoon" /tr "\"%SCRIPT_PATH%\"" /sc daily /st 14:00 /f
schtasks /create /tn "YouTubeAutomation_Evening" /tr "\"%SCRIPT_PATH%\"" /sc daily /st 19:00 /f

echo [INFO] Tasks registered successfully.
pause
endlocal
