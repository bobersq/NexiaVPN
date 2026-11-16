@echo off
chcp 65001 >nul 2>&1

echo NexiaVPN - Starting...
echo.

:: Check Python exists
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found.
    echo Install Python 3.10+ from https://python.org
    echo Check 'Add Python to PATH' during install.
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo [OK] Python %PYVER% found

:: Detect if Python 3.10 (needs older PySide6)
echo %PYVER% | findstr /b "3.10" >nul
if %errorlevel% equ 0 (
    echo [INFO] Python 3.10 detected - installing compatible PySide6...
    pip install "PySide6>=6.4.0,<6.6.0" requests --quiet --disable-pip-version-check
    goto :launch
)

:: Python 3.11+ - install latest PySide6
echo [INFO] Installing dependencies...
pip install -r requirements.txt --quiet --disable-pip-version-check
if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies.
    echo Try manually: pip install PySide6 requests
    pause
    exit /b 1
)

:launch
echo [OK] Dependencies ready

if not exist "config" mkdir config
if not exist "logs" mkdir logs
if not exist "bin" mkdir bin
if not exist "assets" mkdir assets

echo [INFO] Launching NexiaVPN...
echo.

python main.py

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Application crashed. See logs\ folder.
    pause
)
