@echo off
chcp 65001 >nul
title Xray Multi-Port Manager 打包工具
color 0A

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║        Xray Multi-Port Manager - EXE 打包工具               ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

:: 检查 PyInstaller
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [信息] 正在安装 PyInstaller...
    pip install pyinstaller
)

:: 安装依赖
echo [步骤 1/3] 安装项目依赖...
pip install -r requirements.txt

:: 清理旧构建
echo [步骤 2/3] 清理旧构建文件...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

:: 执行打包
echo [步骤 3/3] 开始打包...
echo.

pyinstaller --clean ^
    --noconfirm ^
    --onefile ^
    --windowed ^
    --name "XrayMultiPortManager" ^
    --add-data "xray_gui;xray_gui" ^
    --hidden-import PyQt6 ^
    --hidden-import PyQt6.QtCore ^
    --hidden-import PyQt6.QtGui ^
    --hidden-import PyQt6.QtWidgets ^
    --hidden-import aiohttp ^
    --exclude-module matplotlib ^
    --exclude-module numpy ^
    --exclude-module pandas ^
    --exclude-module scipy ^
    --exclude-module PIL ^
    --exclude-module tkinter ^
    --exclude-module PySide6 ^
    --exclude-module PyQt5 ^
    xray_manager.py

if errorlevel 1 (
    echo.
    echo [错误] 打包失败！
    pause
    exit /b 1
)

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                    ✓ 打包成功！                               ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo 生成文件: dist\XrayMultiPortManager.exe
echo.
echo 注意：运行时需要将 xray.exe 放在同一目录下！
echo.

:: 复制必要文件到 dist
echo 正在复制运行时文件...
if exist xray.exe copy xray.exe dist\ >nul

echo.
echo 所有文件已准备就绪！
echo.
pause
