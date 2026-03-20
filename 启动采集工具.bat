@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"

echo ============================================
echo   XHS Spider - Starting...
echo ============================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.8+
    echo Download: https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH"
    pause
    exit /b 1
)

echo [INFO] Installing dependencies...
pip install flask requests loguru python-dotenv retry openpyxl PyExecJS
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies. Check your network.
    pause
    exit /b 1
)

echo [INFO] Starting web GUI, browser will open automatically...
echo.
python gui_web.py
pause
