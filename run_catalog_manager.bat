@echo off
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  set "PYTHON_CMD=python"
) else (
  set "PYTHON_CMD=py -3"
)

%PYTHON_CMD% -m pip install -r scripts\requirements.txt
if errorlevel 1 (
  echo.
  echo Failed to install Python requirements.
  pause
  exit /b 1
)

%PYTHON_CMD% local_catalog_manager.py
if errorlevel 1 (
  echo.
  echo Catalog manager exited with an error.
  pause
  exit /b 1
)
