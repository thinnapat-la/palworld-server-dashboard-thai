@echo off
setlocal
cd /d "%~dp0\..\.."
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\run\windows\PalworldManager.ps1" -Action "%~1" %2 %3 %4 %5 %6 %7 %8 %9
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo.
  echo Operation failed. Read the error above, then press any key.
  pause >nul
)
exit /b %RC%
