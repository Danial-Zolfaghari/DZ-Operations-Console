@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title DZ Control

set "PYTHON_EXE="
where py >nul 2>nul && set "PYTHON_EXE=py"
if not defined PYTHON_EXE (
  where python >nul 2>nul && set "PYTHON_EXE=python"
)
if not defined PYTHON_EXE (
  echo [ERROR] Python was not found in PATH.
  echo Install Python 3.11+ and enable "Add Python to PATH".
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [DZ] Creating virtual environment...
  %PYTHON_EXE% -m venv .venv
  if errorlevel 1 goto :fail
  echo [DZ] Installing dependencies...
  ".venv\Scripts\python.exe" -m pip install --upgrade pip
  if errorlevel 1 goto :fail
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 goto :fail
) else (
  ".venv\Scripts\python.exe" -c "import flask,psutil,mss,cv2,numpy,pyautogui" >nul 2>nul
  if errorlevel 1 (
    echo [DZ] Repairing missing dependencies...
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 goto :fail
  )
)


echo.
echo [DZ] Starting DZ Control...
echo [DZ] Open http://127.0.0.1:5000
echo [DZ] Default login: admin / admin123
echo.
".venv\Scripts\python.exe" run.py
set "EXIT_CODE=%ERRORLEVEL%"
echo.
echo [DZ] Application stopped with exit code %EXIT_CODE%.
pause
exit /b %EXIT_CODE%

:fail
echo.
echo [ERROR] DZ Control could not start.
pause
exit /b 1
