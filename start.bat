@echo off
REM Double-click to start LeRobot Plug and Play on Windows.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
if errorlevel 1 pause
