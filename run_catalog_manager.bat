@echo off
cd /d "%~dp0"
py -3 -m pip install -r scripts\requirements.txt
if errorlevel 1 exit /b 1
py -3 local_catalog_manager.py
