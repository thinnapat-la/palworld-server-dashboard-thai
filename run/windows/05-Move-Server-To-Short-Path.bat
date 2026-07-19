@echo off
chcp 65001 >nul
echo.
echo This tool copies PalServer and World data to a short Windows path such as C:\PalServer.
echo Use it only when the current path is long or Palworld reports Save/Backup copy errors.
echo The original folder is not deleted automatically.
echo.
set /p "CONFIRM=Type MOVE to continue, or press Enter to cancel: "
if /I not "%CONFIRM%"=="MOVE" exit /b 0
call "%~dp0_Run-Manager.bat" relocate-host
if not errorlevel 1 pause
