@echo off
cd /d "%~dp0.."
python .\src\emulator.py --script-path .\startup.txt
pause