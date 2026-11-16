@echo off
chcp 65001 >nul 2>&1
title NexiaVPN Builder

echo ============================================
echo   NexiaVPN - Build EXE
echo ============================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found!
    pause
    exit /b 1
)

echo [1/4] Installing PyInstaller...
pip install pyinstaller --quiet
if %errorlevel% neq 0 (
    echo ERROR: PyInstaller install failed
    pause
    exit /b 1
)

echo [2/4] Installing dependencies...
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo ERROR: Dependencies install failed
    pause
    exit /b 1
)

echo [3/4] Cleaning previous build...
if exist "dist" rmdir /s /q dist
if exist "build" rmdir /s /q build
if exist "NexiaVPN.spec" del /q NexiaVPN.spec

echo [4/4] Building EXE...
pyinstaller ^
    --name NexiaVPN ^
    --onefile ^
    --windowed ^
    --add-data "assets;assets" ^
    --hidden-import PySide6.QtCore ^
    --hidden-import PySide6.QtGui ^
    --hidden-import PySide6.QtWidgets ^
    --hidden-import PySide6.QtNetwork ^
    --collect-all PySide6 ^
    --noconfirm ^
    main.py

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Build failed!
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Build complete!
echo   Output: dist\NexiaVPN.exe
echo ============================================
echo.

if exist "bin" (
    xcopy /E /I /Y "bin" "dist\bin" >nul
    echo [OK] bin\ copied to dist\bin\
)

echo Done! See dist\NexiaVPN.exe
pause
