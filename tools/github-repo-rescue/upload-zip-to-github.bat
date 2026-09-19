@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0upload-zip-to-github.ps1"
pause
