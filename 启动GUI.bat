@echo off
chcp 65001 >nul
cd /d "%~dp0"
python xray_manager.py
pause
