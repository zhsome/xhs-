#!/bin/bash
echo "============================================"
echo "  小红书数据采集工具 - 启动中..."
echo "============================================"
echo

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未检测到 Python3，请先安装"
    exit 1
fi

# 安装依赖（首次运行）
if [ ! -f ".deps_installed" ]; then
    echo "[信息] 首次运行，正在安装依赖..."
    pip3 install flask requests loguru python-dotenv retry openpyxl PyExecJS -q
    if [ $? -eq 0 ]; then
        touch .deps_installed
        echo "[信息] 依赖安装完成"
    else
        echo "[错误] 依赖安装失败"
        exit 1
    fi
fi

echo "[信息] 正在启动，浏览器将自动打开..."
echo
python3 gui_web.py
