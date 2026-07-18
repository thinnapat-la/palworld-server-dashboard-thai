@echo off
call "%~dp0_Run-Manager.bat" relocate-host
if not errorlevel 1 pause
