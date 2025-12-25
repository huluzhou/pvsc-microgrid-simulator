@echo off
REM pyenv-win 设置和Python 3.10.11安装脚本（使用清华镜像源）

echo === pyenv-win Python环境设置（使用清华镜像源）===
echo.

REM 设置pyenv路径
set PYENV_ROOT=%USERPROFILE%\.pyenv
set PYENV_BIN=%PYENV_ROOT%\pyenv-win\bin
set PYENV_SHIMS=%PYENV_ROOT%\pyenv-win\shims
set PYENV_CACHE=%PYENV_ROOT%\pyenv-win\install_cache

REM 添加到PATH
set PATH=%PYENV_BIN%;%PYENV_SHIMS%;%PATH%

echo 检查pyenv安装...
call "%PYENV_BIN%\pyenv.bat" --version
if errorlevel 1 (
    echo 错误: 无法运行pyenv
    echo 请确保pyenv-win已正确安装
    pause
    exit /b 1
)

echo.
echo 注意: Python 3.10.19在pyenv-win中不可用
echo 将安装Python 3.10.11（pyenv-win中可用的最新3.10版本）
echo.

REM 确保缓存目录存在
if not exist "%PYENV_CACHE%" mkdir "%PYENV_CACHE%"

REM 从清华镜像源下载Python安装包
set PYTHON_VERSION=3.10.11
set PYTHON_FILE=python-%PYTHON_VERSION%-amd64.exe
set PYTHON_URL=https://mirrors.tuna.tsinghua.edu.cn/python-release/%PYTHON_VERSION%/%PYTHON_FILE%
set PYTHON_CACHE=%PYENV_CACHE%\%PYTHON_FILE%

echo 从清华镜像源下载Python %PYTHON_VERSION%...
echo 下载地址: %PYTHON_URL%
echo 保存位置: %PYTHON_CACHE%
echo.

REM 检查是否已下载
if exist "%PYTHON_CACHE%" (
    echo 发现已存在的安装包，跳过下载
) else (
    echo 正在下载（这可能需要几分钟）...
    powershell -Command "Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_CACHE%'"
    if errorlevel 1 (
        echo.
        echo 警告: 从清华镜像源下载失败，尝试从官方源下载...
        set PYTHON_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/%PYTHON_FILE%
        powershell -Command "Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_CACHE%'"
        if errorlevel 1 (
            echo.
            echo 错误: Python安装包下载失败
            echo 请检查网络连接并重试
            pause
            exit /b 1
        )
    )
    echo 下载完成!
)

echo.
echo 安装Python %PYTHON_VERSION%（使用本地缓存）...
call "%PYENV_BIN%\pyenv.bat" install %PYTHON_VERSION%
if errorlevel 1 (
    echo.
    echo 错误: Python %PYTHON_VERSION%安装失败
    echo 请检查错误信息并重试
    pause
    exit /b 1
)

echo.
echo Python %PYTHON_VERSION%安装成功!

echo.
echo 设置本地Python版本为%PYTHON_VERSION%...
call "%PYENV_BIN%\pyenv.bat" local %PYTHON_VERSION%

echo.
echo 验证Python版本...
python --version

echo.
echo ========================================
echo Python %PYTHON_VERSION%设置完成!
echo ========================================
echo.
echo 现在可以运行 'python setup_venv.py' 创建虚拟环境
echo.
pause

