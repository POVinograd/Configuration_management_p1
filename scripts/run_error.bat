@echo off
cd /d "%~dp0.."
python .\src\emulator.py --script-path .\startup_error.txt
pause