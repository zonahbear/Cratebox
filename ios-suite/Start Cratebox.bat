@echo off
cd /d "%~dp0"
py start_cratebox.py 2>nul || python start_cratebox.py
pause
