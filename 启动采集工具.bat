@echo off
chcp 65001 >nul
title 小红书数据采集工具

echo ============================================
echo   小红书数据采集工具 - 启动中...
echo ============================================
echo.

:: 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python，请先安装 Python 3.8+
    echo 下载地址: https://www.python.org/downloads/
    echo 安装时请勾选 "Add Python to PATH"
    pause
    exit /b 1
)

:: 安装依赖（首次运行）
if not exist ".deps_installed" (
    echo [信息] 首次运行，正在安装依赖...
    pip install flask requests loguru python-dotenv retry openpyxl PyExecJS -q
    if %errorlevel% equ 0 (
        echo. > .deps_installed
        echo [信息] 依赖安装完成
    ) else (
        echo [错误] 依赖安装失败，请检查网络连接
        pause
        exit /b 1
    )
)

echo [信息] 正在启动，浏览器将自动打开...
echo.
python gui_web.py
pause
