@echo off
cd /d "%~dp0.."
python .\src\emulator.py --vfs-path .\vfs\vfs_files.zip
pause