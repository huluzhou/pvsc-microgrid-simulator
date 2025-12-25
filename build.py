#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
打包脚本
用于将PandaPower仿真器打包成可执行文件
"""

import os
import sys
import subprocess
import shutil
import time
from pathlib import Path
from src.config import (
    # 功能标志
    FEATURE_SIMULATION, FEATURE_MODBUS, FEATURE_REPORT, FEATURE_EXPORT,
    # 调试模式标志
    DEBUG_MODE, VERBOSE_LOGGING,
    # 辅助函数和装饰器
    is_feature_enabled, conditional_compile, import_if_enabled
)

def check_venv_env():
    """检查是否在venv环境中"""
    # 检查VIRTUAL_ENV环境变量
    venv_path = os.environ.get('VIRTUAL_ENV')
    if venv_path:
        venv_name = os.path.basename(venv_path)
        print(f"当前venv环境: {venv_name}")
        print(f"venv路径: {venv_path}")
        # 建议使用venv-build环境进行打包
        if 'build' in venv_name.lower():
            print("✓ 检测到打包环境，适合进行构建")
        else:
            print("⚠ 建议使用 venv-build 环境进行打包")
        return True
    else:
        # 检查是否在venv-build目录中运行
        python_exe = sys.executable
        if 'venv-build' in python_exe or 'venv_build' in python_exe:
            print(f"检测到venv-build环境: {python_exe}")
            return True
        else:
            print("警告: 未检测到venv环境")
            print("建议激活 venv-build 环境:")
            if sys.platform == "win32":
                print("  .\\venv-build\\Scripts\\Activate.ps1")
            else:
                print("  source venv-build/bin/activate")
            return False


def check_pyinstaller():
    """检查PyInstaller是否已安装
    
    注意：如果使用requirements-build.txt创建环境，PyInstaller应该已经自动安装
    """
    try:
        import PyInstaller
        print(f"PyInstaller版本: {PyInstaller.__version__}")
        return True
    except ImportError:
        print("PyInstaller未安装，正在安装...")
        print("提示：建议使用 'python setup_venv.py' 创建包含PyInstaller的完整环境")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller==6.15.0"])
            print("PyInstaller通过pip安装成功")
            return True
        except subprocess.CalledProcessError:
            print("PyInstaller安装失败，请手动安装：pip install pyinstaller==6.15.0")
            return False


def clean_build():
    """清理之前的构建文件"""
    dirs_to_clean = ['build', 'dist', '__pycache__']
    
    print("清理构建文件...")
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"清理目录: {dir_name}")
            shutil.rmtree(dir_name)
    
    # 清理.pyc文件
    pyc_count = 0
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.pyc'):
                os.remove(os.path.join(root, file))
                pyc_count += 1
    
    if pyc_count > 0:
        print(f"清理了 {pyc_count} 个.pyc文件")


def build_executable():
    """构建可执行文件"""
    print("\n开始构建可执行文件...")
    
    # 使用简化的PyInstaller命令，避免复杂的spec文件配置问题
    # 排除未使用的PySide6组件以减小可执行文件大小
    if FEATURE_SIMULATION:
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--onedir",
            "--windowed", 
            "--name=pandapower_sim",
            "--upx-dir=upx",
            "--clean",
            "--optimize=2",
            "--add-data=src/assets;assets",
            # 排除未使用的PySide6模块
            "--exclude-module=PySide6.QtBluetooth",
            "--exclude-module=PySide6.QtConcurrent",
            "--exclude-module=PySide6.QtDBus",
            "--exclude-module=PySide6.QtDesigner",
            "--exclude-module=PySide6.QtHelp",
            "--exclude-module=PySide6.QtMultimedia",
            "--exclude-module=PySide6.QtMultimediaWidgets",
            "--exclude-module=PySide6.QtNetwork",
            "--exclude-module=PySide6.QtOpenGL",
            "--exclude-module=PySide6.QtOpenGLWidgets",
            "--exclude-module=PySide6.QtPositioning",
            "--exclude-module=PySide6.QtPrintSupport",
            "--exclude-module=PySide6.QtQml",
            "--exclude-module=PySide6.QtQuick",
            "--exclude-module=PySide6.QtQuickControls2",
            "--exclude-module=PySide6.QtQuickWidgets",
            "--exclude-module=PySide6.QtRemoteObjects",
            "--exclude-module=PySide6.QtScxml",
            "--exclude-module=PySide6.QtSensors",
            "--exclude-module=PySide6.QtSerialPort",
            "--exclude-module=PySide6.QtSql",
            "--exclude-module=PySide6.QtTest",
            "--exclude-module=PySide6.QtWebChannel",
            "--exclude-module=PySide6.QtWebEngine",
            "--exclude-module=PySide6.QtWebEngineCore",
            "--exclude-module=PySide6.QtWebEngineWidgets",
            "--exclude-module=PySide6.QtWebSockets",
            "--exclude-module=PySide6.QtXml",

            # 排除其他可能不需要的模块
            "--exclude-module=tkinter",
            "--exclude-module=Tkinter",
            "--exclude-module=matplotlib.backends.backend_tkagg",
            "--exclude-module=matplotlib.backends.backend_webagg",
            "--exclude-module=matplotlib.backends.backend_qt4agg",
            "--exclude-module=IPython",
            "--exclude-module=jupyter",
            "--exclude-module=notebook",
            "--exclude-module=pytest",
            "--exclude-module=test",
            "--exclude-module=doctest",
            "--exclude-module=distutils",
            "--exclude-module=setuptools",
            "--exclude-module=pkg_resources",
            # 添加隐藏依赖，确保tomli_w被包含在打包中
            "--hidden-import=tomli_w",
            "--hidden-import=tomli",
            "src/main.py"
        ]
    else:
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--onedir",
            "--windowed", 
            "--name=pandapower_sim",
            "--upx-dir=upx",
            "--clean",
            "--optimize=2",
            "--add-data=src/assets;assets",
            # 排除未使用的PySide6模块
            "--exclude-module=PySide6.QtBluetooth",
            "--exclude-module=PySide6.QtConcurrent",
            "--exclude-module=PySide6.QtDBus",
            "--exclude-module=PySide6.QtDesigner",
            "--exclude-module=PySide6.QtHelp",
            "--exclude-module=PySide6.QtMultimedia",
            "--exclude-module=PySide6.QtMultimediaWidgets",
            "--exclude-module=PySide6.QtNetwork",
            "--exclude-module=PySide6.QtOpenGL",
            "--exclude-module=PySide6.QtOpenGLWidgets",
            "--exclude-module=PySide6.QtPositioning",
            "--exclude-module=PySide6.QtPrintSupport",
            "--exclude-module=PySide6.QtQml",
            "--exclude-module=PySide6.QtQuick",
            "--exclude-module=PySide6.QtQuickControls2",
            "--exclude-module=PySide6.QtQuickWidgets",
            "--exclude-module=PySide6.QtRemoteObjects",
            "--exclude-module=PySide6.QtScxml",
            "--exclude-module=PySide6.QtSensors",
            "--exclude-module=PySide6.QtSerialPort",
            "--exclude-module=PySide6.QtSql",
            "--exclude-module=PySide6.QtTest",
            "--exclude-module=PySide6.QtWebChannel",
            "--exclude-module=PySide6.QtWebEngine",
            "--exclude-module=PySide6.QtWebEngineCore",
            "--exclude-module=PySide6.QtWebEngineWidgets",
            "--exclude-module=PySide6.QtWebSockets",
            "--exclude-module=PySide6.QtXml",

            # 排除pandapower及其相关组件
            "--exclude-module=pandapower",
            "--exclude-module=pandapower.converter",
            "--exclude-module=pandapower.control",
            "--exclude-module=pandapower.plotting",
            "--exclude-module=pandapower.pf",
            "--exclude-module=pandapower.opf",
            "--exclude-module=pandapower.shortcircuit",
            "--exclude-module=pandapower.results",
            "--exclude-module=pandapower.timeseries",
            "--exclude-module=numpy",
            "--exclude-module=scipy",
            "--exclude-module=pandas",
            "--exclude-module=matplotlib",
            "--exclude-module=sympy",
            
            # 排除其他可能不需要的模块
            "--exclude-module=tkinter",
            "--exclude-module=Tkinter",
            "--exclude-module=matplotlib.backends.backend_tkagg",
            "--exclude-module=matplotlib.backends.backend_webagg",
            "--exclude-module=matplotlib.backends.backend_qt4agg",
            "--exclude-module=IPython",
            "--exclude-module=jupyter",
            "--exclude-module=notebook",
            "--exclude-module=pytest",
            "--exclude-module=test",
            "--exclude-module=doctest",
            "--exclude-module=distutils",
            "--exclude-module=setuptools",
            "--exclude-module=pkg_resources",
            # 添加隐藏依赖，确保tomli_w被包含在打包中
            "--hidden-import=tomli_w",
            "--hidden-import=tomli",
            "src/main.py"
        ]
        
    
    try:
        print("正在执行PyInstaller...")
        # 直接运行命令，不使用进度条避免死循环
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("\n构建成功!")
        print("可执行文件已生成: dist/pandapower_sim.exe")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n构建失败: {e}")
        print(f"错误输出: {e.stderr}")
        return False
    except Exception as e:
        print(f"\n构建过程中发生异常: {e}")
        return False

def main():
    """主函数"""
    print("=== PandaPower仿真器打包工具 ===")
    
    # 1. 检查venv环境
    print("\n[1/5] 检查venv环境...")
    check_venv_env()
    
    # 2. 检查PyInstaller
    print("\n[2/5] 检查PyInstaller...")
    if not check_pyinstaller():
        return False
    
    # 3. 清理构建文件
    print("\n[3/5] 清理构建文件...")
    clean_build()
    
    # 4. 构建可执行文件
    print("\n[4/5] 构建可执行文件...")
    if not build_executable():
        return False
    
    print("\n" + "="*50)
    print("打包完成!")
    print("="*50)
    print("可执行文件位置: dist/pandapower_sim.exe")
    print("您可以将整个dist文件夹分发给用户")
    print("="*50)
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)