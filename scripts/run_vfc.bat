@echo off
cd /d "%~dp0.."
python .\src\emulator.py --vfs-path .\vfs
pause