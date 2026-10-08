@echo off
cd /d "%~dp0.."
python .\src\emulator.py --script-path .\startup.txt --vfs-path .\vfs\vfs_nested.zip
pause