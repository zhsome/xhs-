# encoding: utf-8
"""
打包脚本 - 将小红书数据采集 GUI 打包为 exe
使用方式（在 Windows 上运行）:
    1. pip install pyinstaller
    2. python build_exe.py
打包完成后 exe 在 dist/ 目录下
"""

import PyInstaller.__main__
import os
import sys

base_dir = os.path.dirname(os.path.abspath(__file__))

# Windows 用 ';' 分隔, Linux/Mac 用 ':'
sep = ';' if sys.platform == 'win32' else ':'

PyInstaller.__main__.run([
    os.path.join(base_dir, 'gui.py'),
    '--name=小红书数据采集工具',
    '--onefile',
    '--windowed',
    # 打包 static 目录下的 js 文件
    f'--add-data={os.path.join(base_dir, "static")}{sep}static',
    # 打包 .env 模板
    f'--add-data={os.path.join(base_dir, ".env")}{sep}.',
    # 隐式导入
    '--hidden-import=requests',
    '--hidden-import=loguru',
    '--hidden-import=openpyxl',
    '--hidden-import=dotenv',
    '--hidden-import=retry',
    '--hidden-import=execjs',
    # 排除不需要的大模块
    '--exclude-module=matplotlib',
    '--exclude-module=numpy',
    '--exclude-module=pandas',
    '--exclude-module=scipy',
    '--exclude-module=PIL',
    # 不弹确认
    '--noconfirm',
    # 工作目录
    f'--distpath={os.path.join(base_dir, "dist")}',
    f'--workpath={os.path.join(base_dir, "build")}',
    f'--specpath={base_dir}',
])

print("\n" + "=" * 50)
print("打包完成！exe 文件在 dist/ 目录下")
print("=" * 50)
