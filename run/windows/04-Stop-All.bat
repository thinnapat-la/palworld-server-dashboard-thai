@echo off
call "%~dp0_Run-Manager.bat" stop-all
if not errorlevel 1 pause
