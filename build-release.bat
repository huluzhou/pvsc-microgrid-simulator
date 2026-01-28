@echo off
REM 构建发布版本的完整流程 (Windows)
REM 1. 打包Python内核
REM 2. 构建前端
REM 3. 构建Tauri应用

echo ==========================================
echo 开始构建发布版本
echo ==========================================

REM 1. 打包Python内核
echo.
echo [1/3] 打包Python内核...
python pack_python_kernel.py
if %errorlevel% neq 0 (
    echo Python内核打包失败
    exit /b 1
)
echo Python内核打包成功

REM 2. 构建前端
echo.
echo [2/3] 构建前端...
call npm run build
if %errorlevel% neq 0 (
    echo 前端构建失败
    exit /b 1
)
echo 前端构建成功

REM 3. 构建Tauri应用
echo.
echo [3/3] 构建Tauri应用...
call npm run tauri build
if %errorlevel% neq 0 (
    echo Tauri应用构建失败
    exit /b 1
)
echo Tauri应用构建成功

echo.
echo ==========================================
echo 构建完成！
echo ==========================================
