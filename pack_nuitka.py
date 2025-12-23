#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Nuitka打包脚本
用于将PandaPower仿真器打包成高性能单文件可执行程序
"""

import os
import sys
import subprocess
import shutil
import time
from pathlib import Path

# 导入配置以获取功能标志
try:
    from src.config import FEATURE_SIMULATION
except ImportError:
    # 如果无法导入，默认为True
    FEATURE_SIMULATION = True

def check_nuitka():
    """检查Nuitka是否已安装"""
    try:
        import nuitka
        try:
            version = nuitka.__version__
        except AttributeError:
            try:
                import importlib.metadata
                version = importlib.metadata.version('nuitka')
            except Exception:
                version = "未知"
        
        print(f"Nuitka版本: {version}")
        return True
    except ImportError:
        print("Nuitka未安装，正在安装...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "nuitka", "zstandard"])
            print("Nuitka安装成功")
            return True
        except subprocess.CalledProcessError:
            print("Nuitka安装失败，请手动安装: pip install nuitka zstandard")
            return False

def clean_build():
    """清理之前的构建文件"""
    dirs_to_clean = [
        'build', 'dist', 
        'pandapower_sim.build', 'pandapower_sim.dist', 'pandapower_sim.onefile-build',
        'main.build', 'main.dist', 'main.onefile-build'
    ]
    
    print("清理构建文件...")
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"清理目录: {dir_name}")
            shutil.rmtree(dir_name)
            
    # 清理可能存在的spec文件（虽然Nuitka不用，但清理一下保持整洁）
    for file in os.listdir('.'):
        if file.endswith('.spec'):
            os.remove(file)

def build_executable():
    """使用Nuitka构建可执行文件"""
    print("\n开始使用Nuitka构建可执行文件...")
    
    # Nuitka基础命令
    cmd = [
        sys.executable, "-m", "nuitka",
        "--standalone",           # 包含所有依赖
        "--onefile",              # 生成单文件
        "--show-progress",        # 显示进度
        "--show-memory",          # 显示内存使用
        # "--output-dir=dist",      # 输出目录 (Nuitka bug: avoid using output-dir with onefile)
        # "--output-filename=pandapower_sim.exe", # 输出文件名 (Nuitka bug: leads to AssertionError)
        "--enable-plugin=pyside6", # 启用PySide6插件
        "--windows-disable-console", # 禁用控制台窗口
        "--include-data-dir=src/assets=src/assets", # 包含资源文件，保持目录结构
        "--include-package=tomli_w", # 强制包含tomli_w
    ]
    
    # 排除不必要的模块以减小体积
    # 注意：Nuitka的排除参数是 --nofollow-import-to
    excludes = [
        "tkinter",
        "matplotlib.backends.backend_tkagg",
        "matplotlib.backends.backend_webagg",
        "IPython",
        "jupyter",
        "notebook",
        "pytest",
        "unittest",
        "doctest",
        "setuptools",
        "distutils",
        "pkg_resources",
    ]
    
    if FEATURE_SIMULATION:
        # 排除PySide6中不需要的模块
        excludes.extend([
            "PySide6.QtBluetooth",
            "PySide6.QtConcurrent",
            "PySide6.QtDBus",
            "PySide6.QtDesigner",
            "PySide6.QtHelp",
            "PySide6.QtMultimedia",
            "PySide6.QtMultimediaWidgets",
            "PySide6.QtNetwork",
            "PySide6.QtOpenGL",
            "PySide6.QtOpenGLWidgets",
            "PySide6.QtPositioning",
            "PySide6.QtPrintSupport",
            "PySide6.QtQml",
            "PySide6.QtQuick",
            "PySide6.QtQuickControls2",
            "PySide6.QtQuickWidgets",
            "PySide6.QtRemoteObjects",
            "PySide6.QtScxml",
            "PySide6.QtSensors",
            "PySide6.QtSerialPort",
            "PySide6.QtSql",
            "PySide6.QtTest",
            "PySide6.QtWebChannel",
            "PySide6.QtWebEngine",
            "PySide6.QtWebEngineCore",
            "PySide6.QtWebEngineWidgets",
            "PySide6.QtWebSockets",
            "PySide6.QtXml",
        ])
    else:
        # 如果不启用仿真，还可以排除pandapower等
        excludes.extend([
            "pandapower",
            "numpy",
            "scipy",
            "pandas",
            "matplotlib",
            "sympy"
        ])

    for module in excludes:
        cmd.append(f"--nofollow-import-to={module}")
        
    # 添加入口文件
    cmd.append("src/main.py")
    
    print(f"执行命令: {' '.join(cmd)}")
    
    start_time = time.time()
    try:
        # 使用subprocess.run执行命令
        subprocess.run(cmd, check=True)
        
        # 重命名输出文件
        src_exe = "main.exe"
        
        # 确保dist目录存在
        if not os.path.exists("dist"):
            os.makedirs("dist")
            
        dst_exe = os.path.join("dist", "pandapower_sim.exe")
        
        if os.path.exists(src_exe):
            if os.path.exists(dst_exe):
                os.remove(dst_exe)
            shutil.move(src_exe, dst_exe)
            print(f"移动并重命名: {src_exe} -> {dst_exe}")
        else:
            print(f"警告: 未找到生成的 {src_exe}")
        
        end_time = time.time()
        duration = end_time - start_time
        print(f"\n构建成功! 耗时: {duration:.2f}秒")
        print("可执行文件已生成: dist/pandapower_sim.exe")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n构建失败: {e}")
        return False
    except Exception as e:
        print(f"\n构建过程中发生异常: {e}")
        return False

def main():
    """主函数"""
    print("=== PandaPower仿真器 Nuitka打包工具 ===")
    print("此工具将使用Nuitka编译Python代码为C++并生成高性能可执行文件")
    
    # 1. 检查环境
    print("\n[1/4] 检查环境...")
    if not check_nuitka():
        return False
        
    # 2. 清理构建文件
    print("\n[2/4] 清理构建文件...")
    clean_build()
    
    # 3. 构建可执行文件
    print("\n[3/4] 构建可执行文件...")
    if not build_executable():
        return False
        
    print("\n" + "="*50)
    print("打包完成!")
    print("="*50)
    print("可执行文件位置: dist/pandapower_sim.exe")
    print("="*50)
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
